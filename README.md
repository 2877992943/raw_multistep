# raw_multistep

## 1，安装
bash install_script.sh

## 2. 运行

程序的入口是 `run_example1.py` 文件。

运行时需要设置两个参数：
- `maxstep`: 最大步数
- `instr`: 指令

## 3. 结束

程序的结束状态有两种：

- **'DONE'**：在最大步数之内完成。执行结束，依据是模型预测的 `finish` 动作。
- **'FAIL'**：未在最大步数之内完成。执行结束。
