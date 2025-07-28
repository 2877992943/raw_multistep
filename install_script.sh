# 安装系统依赖
sudo apt-get update
sudo apt-get install -y python3-pip scrot xvfb

# 创建虚拟环境
python3 -m venv uitars_env
source uitars_env/bin/activate

# 安装 Python 依赖
pip install -r requirements.txt