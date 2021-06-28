import os
import re
import shutil
import subprocess
import time
import uuid
import xml.etree.ElementTree as ET
from multiprocessing import Queue , Process

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from PIL import Image

import Tools

sns.set_style('darkgrid')


class Work:
    status_codes = {
        200: "success" ,
        401: "文件不完整" ,
        402: "文件格式错误,应为xlsx结尾" ,
        501: "请求方式错误" ,
    }

    def __init__(self , uid , status_code=200):
        self.uid = uid
        self.status_code = status_code
        self.q = Queue()

        self.work_dir = os.path.join(Tools.Tools.store_dir , str(uid))
        self.excel_path = os.path.join(self.work_dir , f"{uid}.xlsx")
        self.dat_path = os.path.join(self.work_dir , f"BORON.DAT")
        self.output_dat_path = os.path.join(self.work_dir , f"OUTPUT.DAT")

        self.csv_path = os.path.join(self.work_dir , f"集总参数.csv")
        self.fb_path = os.path.join(self.work_dir , "分布参数")
        self.jz_path = os.path.join(self.work_dir , "集总参数")
        self.data_output_path = os.path.join(self.jz_path , "data")
        self.img_output_path = os.path.join(self.jz_path , "image")
        self.gif_output_path = os.path.join(self.fb_path , "gif")
        self.jz_img_path = os.path.join(self.jz_path , "image" , "集总参数.png")
        self.jz_data_path = os.path.join(self.jz_path , "data" , "集总参数.xlsx")
        self.fb_data_path = os.path.join(self.fb_path , "data")
        self.fb_img_path = os.path.join(self.fb_path , "image")
        self.ASSEMBLY_POWER_DISTRIBUTION = os.path.join(self.fb_data_path , "2D_ASSEMBLY_POWER_DISTRIBUTION")
        self.AXIAL_POWER_DISTRIBUTION = os.path.join(self.fb_data_path , "AXIAL_POWER_DISTRIBUTION")
        self.ASSEMBLY_POWER_DISTRIBUTION_img = os.path.join(self.fb_img_path , "2D_ASSEMBLY_POWER_DISTRIBUTION")
        self.AXIAL_POWER_DISTRIBUTION_img = os.path.join(self.fb_img_path , "AXIAL_POWER_DISTRIBUTION")
        self.AXIAL_POWER_DISTRIBUTION_gif = os.path.join(self.gif_output_path , "AXIAL_POWER_DISTRIBUTION")
        self.ASSEMBLY_POWER_DISTRIBUTION_gif = os.path.join(self.gif_output_path , "2D_ASSEMBLY_POWER_DISTRIBUTION")

    @property
    def info(self):
        return Tools.Tools.get_info(self.excel_path)

    @property
    def msg(self):
        return Work.status_codes[self.status_code]

    # 建立文件夹
    def mkdir(self):
        try:
            os.mkdir(self.jz_path)
            os.mkdir(self.fb_path)
            os.mkdir(self.fb_data_path)
            os.mkdir(self.fb_img_path)
            os.mkdir(self.data_output_path)
            os.mkdir(self.img_output_path)
            os.mkdir(self.gif_output_path)
            os.mkdir(self.AXIAL_POWER_DISTRIBUTION)
            os.mkdir(self.ASSEMBLY_POWER_DISTRIBUTION)
            os.mkdir(self.AXIAL_POWER_DISTRIBUTION_img)
            os.mkdir(self.ASSEMBLY_POWER_DISTRIBUTION_img)
            os.mkdir(self.AXIAL_POWER_DISTRIBUTION_gif)
            os.mkdir(self.ASSEMBLY_POWER_DISTRIBUTION_gif)
        except:
            pass

    # 文件预处理
    def pre_process(self , temp_store_path):
        os.mkdir(self.work_dir)

        self.mkdir()
        shutil.move(temp_store_path , self.excel_path)
        Tools.Tools.gen_xml(self.uid , self.info , self.work_dir)
        shutil.copytree(os.path.join(Tools.Tools.core_dir , "LILAC") , os.path.join(self.work_dir , "LILAC"))
        shutil.copy(os.path.join(Tools.Tools.core_dir , "simplidep.dat") ,
                    os.path.join(self.work_dir , "simplidep.dat"))

    # 改变工作目录并调用
    def _call_core(self):
        os.chdir(self.work_dir)
        subprocess.getstatusoutput(Tools.Tools.bin_path)

    # 监测文件变化
    def _inspect_change(self):
        data = []
        last_content = ''
        while True:
            time.sleep(0.5)
            try:
                with open(self.dat_path , "r") as File:
                    current_content = File.read()
            except BaseException:  # 文件不存在
                continue
            if current_content == last_content:  # 文件无变化
                continue

            diff = current_content.replace(last_content , '')
            last_content = current_content
            diff = re.sub('\\s+' , ' ' , diff).split(' ')[1:-1]
            if len(diff) == 5:
                data.append(diff)
                print(diff)
                self.q.put(diff)  # 放进队列
                pd.DataFrame(data).to_csv(self.csv_path , index=False , header=False)

    # 输出文件处理
    def _process_output(self):

        File = open(self.output_dat_path , "r")
        content = File.read()
        pattern = "AXIAL POWER DISTRIBUTION(.*?)3D ASSEMBLY POWER DISTRIBUTION"
        res = re.findall(pattern , content , re.S)
        axi_powers = [i.strip().split('\n       ') for i in res]
        for index , axi_power in enumerate(axi_powers):
            pd.DataFrame(axi_power).to_excel(os.path.join(self.AXIAL_POWER_DISTRIBUTION , f"Step{index + 1}.xlsx") ,
                                             index=False ,
                                             header=['功率密度'])

        pattern1 = r"2D ASSEMBLY POWER DISTRIBUTION(.*?)BURNUP DISTRIBUTION "
        res = re.findall(pattern1 , content , re.S)
        assem_powers = [[j.split(' ') for j in i.strip().split('\n       ')] for i in res]
        for index , assem_powers in enumerate(assem_powers):
            pd.DataFrame(assem_powers).to_excel(
                os.path.join(self.ASSEMBLY_POWER_DISTRIBUTION , f"Step{index + 1}.xlsx") ,
                index=False , header=None)

        File.close()

    # 集总参数画图
    def _jz_plot(self):
        df = pd.read_excel(self.jz_data_path)[["天数" , "硼浓度" , "AO"]].values
        x = df[: , 0]
        y1 = df[: , 1]
        y2 = df[: , 2]
        fig = plt.figure()
        ax1 = fig.add_subplot(111)
        ln1 = ax1.plot(x , y1 , label="Boron density" , marker='*')
        ax1.set_ylabel('Boron density/ppm')
        ax1.set_xlabel('Time/d')
        ax1.set_title("Boron density, AO-Time")
        ax2 = ax1.twinx()
        ax2.set_ylabel("AO")
        ln2 = ax2.plot(x , y2 , 'r' , label="AO" , marker='o')
        lns = ln1 + ln2
        labs = [l.get_label() for l in lns]
        ax1.legend(lns , labs , loc="upper center")
        plt.tight_layout()
        plt.savefig(self.jz_img_path , dpi=300)
        plt.clf()

    # 分布参数画图
    def _fb_plot(self):
        root , dirs , files = next(os.walk(self.AXIAL_POWER_DISTRIBUTION , topdown=True))
        files.sort()
        for index , file in enumerate(files):
            # print(files)
            df = pd.read_excel(os.path.join(self.AXIAL_POWER_DISTRIBUTION , file))[["功率密度"]].values
            df = [i[0] for i in df.tolist()]
            plt.barh(range(7) , df , height=1)
            plt.xlabel("Power/MW")
            plt.ylabel("Height")
            plt.xlim((0 , 1.4))
            plt.title(f"Axial Power Distribution Step{index + 1}")
            plt.savefig(os.path.join(self.AXIAL_POWER_DISTRIBUTION_img , file.replace("xlsx" , "png")) , dpi=300)
            # plt.show()
            plt.clf()

        root , dirs , files = next(os.walk(self.ASSEMBLY_POWER_DISTRIBUTION , topdown=True))
        files.sort()
        for index , file in enumerate(files):
            df = pd.read_excel(os.path.join(self.ASSEMBLY_POWER_DISTRIBUTION , file) , header=None)
            plt.figure(dpi=120)
            sns.heatmap(data=df , mask=df == 0 , annot=True , vmin=0 , vmax=1.5 , fmt=".2f" , yticklabels=False ,
                        xticklabels=False)
            plt.title(f"Assembly Power Distribution Step{index + 1}")
            plt.savefig(os.path.join(self.ASSEMBLY_POWER_DISTRIBUTION_img , file.replace("xlsx" , "png")) , dpi=300)
            # plt.show()
            plt.clf()

    # 生成动图
    @staticmethod
    def _gen_gif(input_dir , output_path):
        root , dirs , files = next(os.walk(input_dir , topdown=True))
        images = []
        count = 1
        while True:
            if f"Step{count}.png" not in files:
                break
            else:
                new_frame = Image.open(os.path.join(input_dir , f"Step{count}.png"))
                images.append(new_frame)
            count += 1

        im = images[0]

        im.save(os.path.join(output_path) , format="GIF" , save_all=True , append_images=images[1:] , loop=1 ,
                duration=300)

    # 生成gif
    def _gif_plot(self):
        self._gen_gif(os.path.join(self.ASSEMBLY_POWER_DISTRIBUTION_img , ) ,
                      os.path.join(self.ASSEMBLY_POWER_DISTRIBUTION_gif , "径向功率分布.gif"))
        self._gen_gif(os.path.join(self.AXIAL_POWER_DISTRIBUTION_img) ,
                      os.path.join(self.AXIAL_POWER_DISTRIBUTION_gif , "轴向功率分布.gif"))

    # 清理多余文件
    def _clean(self):
        file_remain = ["CORE.xml" , "BUCO.DAT" , f"{self.uid}.xlsx" , "info"]
        dir_remain = ["集总参数" , "分布参数"]
        root , dirs , files = next(os.walk(self.work_dir , topdown=True))
        for dir in dirs:
            if dir not in dir_remain:
                shutil.rmtree(os.path.join(self.work_dir , dir))
        for file in files:
            if file not in file_remain:
                os.remove(os.path.join(self.work_dir , file))

    # 后续处理和图表生成
    def process_data(self):

        df = pd.read_csv(self.csv_path , header=None)
        df.to_excel(self.jz_data_path , header=["步骤" , "天数" , "燃耗深度" , "硼浓度" , "AO"] , index=False)
        self._process_output()
        self._jz_plot()
        self._fb_plot()
        self._gif_plot()
        self._clean()

    # 主要工作
    def main_work(self):
        self.mkdir()
        call_process = Process(target=self._call_core)
        inspect_process = Process(target=self._inspect_change)
        inspect_process.start()
        call_process.start()
        call_process.join()
        time.sleep(0.5)
        inspect_process.terminate()
        self.q.put(-1)
        self.process_data()

    # 获取某步轴向分布参数
    def get_n_step_axial(self , n):
        data_path = os.path.join(self.AXIAL_POWER_DISTRIBUTION , f"Step{n}.xlsx")
        return [i[0] for i in pd.read_excel(data_path).values.tolist()]

    # 获取某步径向分布参数
    def get_n_step_assembly(self , n):
        data_path = os.path.join(self.ASSEMBLY_POWER_DISTRIBUTION , f"Step{n}.xlsx")
        return pd.read_excel(data_path , header=None).values.tolist()

    # 结果导出
    def export(self , data , img , gif):
        file_name = f"output-{self.uid[:8]}-{int(time.time()) % 1000}"
        temp_path = os.path.join(Tools.Tools.temp_dir , file_name)
        jz_temp_path = os.path.join(temp_path , "集总参数")
        fb_temp_path = os.path.join(temp_path , "分布参数")
        os.mkdir(temp_path)
        if data:
            jz_data_path = os.path.join(self.jz_path , "data")
            fb_data_path = os.path.join(self.fb_path , "data")
            shutil.copytree(jz_data_path , os.path.join(jz_temp_path , "data"))
            shutil.copytree(fb_data_path , os.path.join(fb_temp_path , "data"))

        if img:
            jz_img_path = os.path.join(self.jz_path , "image")
            fb_img_path = os.path.join(self.fb_path , "image")
            shutil.copytree(jz_img_path , os.path.join(jz_temp_path , "image"))
            shutil.copytree(fb_img_path , os.path.join(fb_temp_path , "image"))
        if gif:
            fb_gif_path = os.path.join(self.fb_path , "gif")
            shutil.copytree(fb_gif_path , os.path.join(fb_temp_path , "gif"))

        target_path = os.path.join(Tools.Tools.output_path , f"{file_name}.zip")
        Tools.Tools.make_zip(temp_path , target_path)
        shutil.rmtree(temp_path)
        return (target_path , f"{file_name}.zip")

    # 复用文件生成
    def recover_work(self , from_uid , step):
        new_uid = uuid.uuid4()
        work_dir = os.path.join(Tools.Tools.store_dir , str(new_uid))
        from_dir = os.path.join(Tools.Tools.store_dir , from_uid)
        buco_path = os.path.join(from_dir , "BUCO.DAT")
        buci_path = os.path.join(work_dir , "BUCI.DAT")
        os.mkdir(work_dir)
        shutil.copy(os.path.join(from_dir , f"{from_uid}.xlsx") , os.path.join(work_dir , f"{new_uid}.xlsx"))
        shutil.copytree(os.path.join(Tools.Tools.core_dir , "LILAC") , os.path.join(work_dir , "LILAC"))
        shutil.copytree(os.path.join(from_dir , f"集总参数") , os.path.join(work_dir , "集总参数"))
        shutil.copytree(os.path.join(from_dir , f"分布参数") , os.path.join(work_dir , "分布参数"))

        shutil.copy(os.path.join(Tools.Tools.core_dir , "simplidep.dat") , os.path.join(work_dir , "simplidep.dat"))

        with open(buco_path , "r") as f:
            content = Tools.Tools.get_step(f.read() , step)
        with open(buci_path , "w") as f:
            f.write(content)

        Tools.Tools.recover_xml(from_uid , new_uid , step)
        return new_uid

    # 添加数据
    def add_param(self , data):
        print(data)
        data = [{"XXPO": 24.9921 , "PXPO": 1 , "TCOOLIN": 565 , "PCRO": [121.504 , 121.504 , 121.504]} ,
                {"XXPO": 24.9921 , "PXPO": 1 , "TCOOLIN": 565 , "PCRO": [121.504 , 121.504 , 121.504]} ,
                {"XXPO": 24.9921 , "PXPO": 1 , "TCOOLIN": 565 , "PCRO": [121.504 , 121.504 , 121.504]}]
        point_num = len(data)
        core_path = os.path.join(self.work_dir , "CORE.xml")
        tree = ET.parse(core_path)

        root = tree.getroot()
        previous_point_num = int(root.find("BURNUP").find("NXP").text)
        root.find("BURNUP").find("NXP").text = str(previous_point_num + point_num)
        for count , i in enumerate(data):
            root.find("BURNUP").find("XXPO").text += f" {i['XXPO']}"
            root.find("BURNUP").find("PXPO").text += f" {i['PXPO']}"
            root.find("THERMAL").find("TCOOLIN").text += f" {i['TCOOLIN']}"
            root.find("CONTROLROD").find(
                "PCRO").text += f"\n{previous_point_num + count + 1}, {', '.join([str(j) for j in i['PCRO']])}"

        tree.write(core_path)


if __name__ == "__main__":
    uid = "359fac0e-692c-4478-90b1-f50cab882d6f"
    work = Work(uid)
    print(work.export(True , True , True))
