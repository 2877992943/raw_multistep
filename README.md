# raw_multistep

1，安装
bash install_script.sh

2, 运行
入口是 run_example1.py
参数设置 :maxstep,instr

3,结束
'DONE' ：在最大步数之内完成， 执行结束，依据是 model预测的finish动作
'FAIL' ：未在最大步数之内完成， 执行结束
