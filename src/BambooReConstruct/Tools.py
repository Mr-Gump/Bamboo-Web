import re
import uuid
import xml.etree.ElementTree as ET
import zipfile

import pandas as pd
from pyecharts import options as opts
from pyecharts.charts import Bar , HeatMap
from pyecharts.globals import ThemeType

import Work
from BambooReConstruct.settings import *


class Tools:
    # 临时文件目录
    temp_dir = os.path.join(BASE_DIR , "temp")

    # 静态资源目录
    static_dir = os.path.join(STATICFILES_DIRS[0] , "file")

    # 存储目录
    store_dir = os.path.join(BASE_DIR , "store")

    # Bamboo-Core 文件目录
    core_dir = os.path.join(static_dir , "Bamboo-Core")

    # 二进制文件路径
    bin_path = os.path.join(core_dir , "Bamboo-Core")

    # 结果导出目录
    output_path = os.path.join(STATICFILES_DIRS[0] , "output")

    # 文件分块
    @staticmethod
    def file_iterator(file_name , chunk_size=10240):
        with open(file_name , "rb") as f:
            while True:
                c = f.read(chunk_size)
                if c:
                    yield c
                else:
                    break

    # 预检查
    @staticmethod
    def pre_check(file_name , file_chunks):
        # 检查文件类型
        if not file_name.endswith(".xlsx"):
            return 402

        status_code = 200
        temp_store_path = os.path.join(Tools.temp_dir , file_name)

        # 写入文件
        with open(temp_store_path , "wb") as File:
            for chunk in file_chunks:
                File.write(chunk)

        # 检查文件完整性
        df = pd.read_excel(temp_store_path)
        if True in list(df.isnull().any()):
            status_code = 401

        return (status_code , temp_store_path)

    # 小时-天数转化
    @staticmethod
    def _div(x):
        return round(x / 24 , 4)

    # 获取excel信息
    @staticmethod
    def get_info(file_path):
        df = pd.read_excel(file_path , dtype=object)
        row , columns = df.shape
        point_num = str(row)
        rod_num = str(columns - 4)
        time_points = ' '.join(df.iloc[: , 1].diff().fillna(0).apply(Tools._div).apply(str).values.tolist())
        p_rate = ' '.join(df.iloc[: , 2].apply(str).values.tolist())
        cool_temp = ' '.join(df.iloc[: , 3].apply(str).values.tolist())
        rod = df.iloc[: , 4:].astype(str).values.tolist()
        rod_loc = '\n'.join([f"{index + 1}, " + ', '.join(i) for index , i in enumerate(rod)])
        return {"NXP": point_num , "XXPO": time_points , "PXPO": p_rate , "TCOOLIN": cool_temp , "PCRO": rod_loc ,
                "NCB": rod_num}

    # 生成xml文件
    @staticmethod
    def gen_xml(uid , info , work_dir):
        xml_path = os.path.join(work_dir , "CORE.xml")
        tree = ET.parse(os.path.join(Tools.core_dir , 'CORE.xml'))
        root = tree.getroot()
        root.find("BURNUP").find("NXP").text = info["NXP"]
        root.find("BURNUP").find("XXPO").text = info["XXPO"]
        root.find("BURNUP").find("PXPO").text = info["PXPO"]
        root.find("THERMAL").find("TCOOLIN").text = info["TCOOLIN"]
        root.find("CONTROLROD").find("PCRO").text = info["PCRO"]
        root.find("CONTROLROD").find("NCB").text = info["NCB"]
        tree.write(xml_path)
        with open(os.path.join(work_dir , "info") , "w") as f:
            f.write(str(uid) + "\n" + info["XXPO"])

    # 处理上传文件
    @staticmethod
    def handle_uploaded_file(file_name , file_chunks):

        status_code , temp_store_path = Tools.pre_check(file_name , file_chunks)

        # 状态码不是200直接返回
        if status_code != 200:
            os.remove(temp_store_path)
            return Work.Work(-1 , status_code)

        uid = uuid.uuid4()
        work = Work.Work(uid , 200)
        work.pre_process(temp_store_path)
        return work

    # 生成轴向分布html
    @staticmethod
    def _gen_axial_graph(data , n):
        c = (
            Bar(init_opts=opts.InitOpts(theme=ThemeType.LIGHT))
                .add_xaxis([i + 1 for i in range(len(data))])
                .add_yaxis("轴向功率" , data , category_gap=0)
                .reversal_axis()
                .set_series_opts(label_opts=opts.LabelOpts(position="right"))
                .set_global_opts(
                title_opts=opts.TitleOpts(title=f"Step{n} 轴向功率分布") ,
                toolbox_opts=opts.ToolboxOpts() ,
                legend_opts=opts.LegendOpts(is_show=False) ,
            )
                .render_embed()
        )
        return re.findall("<body[^>]*>([\s\S]*)<\/body>" , c)[0]

    # 生成径向分布html
    @staticmethod
    def _gen_assembly_graph(data , n):
        value = [[i , j , data[i][j]] for i in range(len(data)) for j in range(len(data[i]))]
        for i in range(len(value)):
            if value[i][2] == 0:
                value[i][2] = '-'

        c = (
            HeatMap()
                .add_xaxis([i + 1 for i in range(len(data))])
                .add_yaxis(
                "功率" ,
                [i + 1 for i in range(len(data[0]))] ,
                value ,
                label_opts=opts.LabelOpts(is_show=True , position="inside") ,
            )
                .set_global_opts(
                title_opts=opts.TitleOpts(title=f"Step{n} 径向功率分布图") ,
                visualmap_opts=opts.VisualMapOpts(min_=0 , max_=1.5 , is_calculable=True) ,
                toolbox_opts=opts.ToolboxOpts() ,
                xaxis_opts=opts.AxisOpts(
                    type_="category" ,
                    splitarea_opts=opts.SplitAreaOpts(
                        is_show=True , areastyle_opts=opts.AreaStyleOpts(opacity=1)
                    ) ,
                ) ,
                yaxis_opts=opts.AxisOpts(
                    type_="category" ,
                    splitarea_opts=opts.SplitAreaOpts(
                        is_show=True , areastyle_opts=opts.AreaStyleOpts(opacity=1)
                    ) ,
                ) ,

            )
                .render_embed()
        )
        return re.findall("<body[^>]*>([\s\S]*)<\/body>" , c)[0]

    # 生成html图像
    @staticmethod
    def gen_graph(uid , n , kind):
        work = Work.Work(uid)
        if kind == 1:
            return Tools._gen_axial_graph(work.get_n_step_axial(n) , n)
        elif kind == 2:
            return Tools._gen_assembly_graph(work.get_n_step_assembly(n) , n)

    # 打包目录为zip文件
    @staticmethod
    def make_zip(source_dir , output_filename):
        zipf = zipfile.ZipFile(output_filename , 'w')
        pre_len = len(os.path.dirname(source_dir))
        for parent , dirnames , filenames in os.walk(source_dir):
            for filename in filenames:
                pathfile = os.path.join(parent , filename)
                arcname = pathfile[pre_len:].strip(os.path.sep)  # 相对路径
                zipf.write(pathfile , arcname)
        zipf.close()

    # 获取历史记录
    @staticmethod
    def scan_history_file():
        result = []
        for root , dirs , files in os.walk(Tools.store_dir , topdown=False):
            for filename in files:
                if filename == "info":
                    with open(os.path.join(root , filename) , "r") as f:
                        content = f.read()
                        uid = content.split('\n')[0]
                        time_points = [float(i) for i in content.split("\n")[1].split(' ')]
                        point_num = len(time_points)
                        result.append({"uid": uid , "point_num": point_num , "time_points": time_points})
        return result

    # 复用xml
    @staticmethod
    def recover_xml(from_uid , uid , step):
        work_dir = os.path.join(Tools.store_dir , str(uid))
        from_dir = os.path.join(Tools.store_dir , from_uid)
        xml_path = os.path.join(work_dir , "CORE.xml")
        tree = ET.parse(os.path.join(from_dir , "CORE.xml"))
        root = tree.getroot()
        root.find("OTset").find("TCal").text = "0 0 0 1 0 0"

        root.find("BURNUP").find("NXP").text = str(step)
        root.find("BURNUP").find("XXPO").text = ' '.join(root.find("BURNUP").find("XXPO").text.split(' ')[:step])
        root.find("BURNUP").find("PXPO").text = ' '.join(root.find("BURNUP").find("PXPO").text.split(' ')[:step])
        root.find("THERMAL").find("TCOOLIN").text = ' '.join(
            root.find("THERMAL").find("TCOOLIN").text.split(' ')[:step])
        root.find("CONTROLROD").find("PCRO").text = '\n'.join(
            root.find("CONTROLROD").find("PCRO").text.split('\n')[:step])

        tree.write(xml_path)

    # 获取某步数据
    @staticmethod
    def get_step(content , step):
        pattern = r'''\-{80}\n Step\s*\d :\s*[0-9]{1,}[.][0-9]* Days\s*[0-9]{1,}[.][0-9]* MWD/tU\s*[0-9]{1,}[.][0-9]* MW\s*[0-9]{1,}[.][0-9]*% FP \n\-{80}'''

        splited = re.split(pattern , content)
        header = re.findall(pattern , content)
        result = []
        for i in range(len(header)):
            result.append(header[i] + splited[i + 1])
        return result[step - 1]


if __name__ == "__main__":
    print(Tools.scan_history_file())
