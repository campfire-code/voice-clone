"""篝火：首次启动的安装脚本 —— 安装 PyTorch 和依赖，并下载预训练模型。

对应上游 install.sh / install.ps1 的步骤，改用 uv + pip，不需要 conda。
"""
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile

root = os.path.dirname(os.path.abspath(__file__))
os.chdir(root)
UV = ["uv", "pip", "install", "--python", sys.executable]


def run(cmd, **kw):
    print(">", " ".join(cmd))
    subprocess.check_call(cmd, **kw)


# 1. PyTorch：Windows 有英伟达显卡用 CUDA 12.6；Mac 用默认版本（Apple 芯片走 MPS）；其余用 CPU 版
system = platform.system()
if system == "Windows" and shutil.which("nvidia-smi"):
    run(UV + ["torch", "torchcodec", "--index-url", "https://download.pytorch.org/whl/cu126"])
elif system == "Darwin":
    run(UV + ["torch", "torchcodec"])
else:
    print("没有检测到英伟达显卡，安装 CPU 版 PyTorch（推理会很慢，训练基本不可用）。")
    run(UV + ["torch", "torchcodec", "--index-url", "https://download.pytorch.org/whl/cpu"])

# 2. 其余依赖
run(UV + ["-r", "extra-req.txt", "--no-deps"])
run(UV + ["-r", "requirements.txt"])
# 用 uv 解析时会选到过旧的 gradio（3.x，和新版 gradio-client 不兼容），而 gradio 4.44 又和新版 starlette 不兼容，这里固定一组能一起工作的版本
run(UV + ["gradio==4.44.1", "starlette<0.47", "fastapi<0.116"])

# 3. 预训练模型。选了国内镜像（UV_DEFAULT_INDEX 有值）时先用 ModelScope，失败再用 HuggingFace
SOURCES = {
    "ModelScope": "https://www.modelscope.cn/models/XXXXRT/GPT-SoVITS-Pretrained/resolve/master/",
    "HF": "https://huggingface.co/XXXXRT/GPT-SoVITS-Pretrained/resolve/main/",
}
order = ["ModelScope", "HF"] if os.environ.get("UV_DEFAULT_INDEX") else ["HF", "ModelScope"]


def fetch(name, dest_dir, check, extract):
    if os.path.exists(check):
        print(f"{name} 已存在，跳过。")
        return
    os.makedirs(dest_dir, exist_ok=True)
    tmp = os.path.join(root, name)
    for src in order:
        url = SOURCES[src] + name
        try:
            print(f"正在下载 {name}（来源 {src}），文件较大，请耐心等待 ...")
            urllib.request.urlretrieve(url, tmp)
            extract(tmp, dest_dir)
            os.remove(tmp)
            return
        except Exception as e:
            print(f"从 {src} 下载失败：{e}")
    raise SystemExit(f"{name} 下载失败，请检查网络后重新运行启动脚本。")


def unzip(path, dest):
    with zipfile.ZipFile(path) as z:
        z.extractall(dest)


def untar(path, dest):
    with tarfile.open(path) as t:
        t.extractall(dest, filter="data")


fetch("pretrained_models.zip", "GPT_SoVITS", "GPT_SoVITS/pretrained_models/sv", unzip)
fetch("G2PWModel.zip", "GPT_SoVITS/text", "GPT_SoVITS/text/G2PWModel", unzip)

import pyopenjtalk  # noqa: E402

jtalk_dir = os.path.dirname(pyopenjtalk.__file__)
if not os.path.exists(os.path.join(jtalk_dir, "open_jtalk_dic_utf_8-1.11")):
    fetch("open_jtalk_dic_utf_8-1.11.tar.gz", jtalk_dir, os.path.join(jtalk_dir, "open_jtalk_dic_utf_8-1.11"), untar)
fetch("nltk_data.zip", sys.prefix, os.path.join(sys.prefix, "nltk_data"), unzip)

if not shutil.which("ffmpeg"):
    print("\n提示：没有找到 ffmpeg。Mac 请先执行 brew install ffmpeg；Windows 请下载 ffmpeg.exe 和 ffprobe.exe 放到本文件夹根目录。")
print("安装完成。")
