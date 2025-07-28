
"""

env
agent
 run task

"""
import os,json
import logging
import datetime
#from uitars_agent_428 import UITARSAgent
from uitars_agent_428_ import UITARSAgent
from env_uos import Env


def run_1example(instruction,maxStep=10,name='1',logging=None,env=None,agent=None,example_result_dir=None):
    logging.info('\n'+instruction+'\n...........\n')
    agent.reset()
    env.reset()

    max_steps=maxStep
    obs = env._get_obs() # Get the initial observation
    done = False
    #instruction='最小化当前应用'
    step_idx = -1



    while not done and step_idx < max_steps:
        logging.info(obs)
        tmp= agent.predict(
            instruction,
            obs
        )
        response, actions=tmp
        logging.info({'response':response,'actions':actions})
        step_idx+=1
        for action in actions:
            print(action)
            # Capture the timestamp before executing the action
            action_timestamp = datetime.datetime.now().strftime("%Y%m%d@%H%M%S")
            logging.info("Step %d: %s", step_idx , action )
            if 'DONE' in action:###模型预测finish
                done=True
            elif 'FAIL' in action:### 超过次数
                done = True
            else:
                obs, reward, done, info = env.step(action  )


            with open(os.path.join(example_result_dir, f"{name}_trajectory.jsonl"), "a") as f:
                f.write(json.dumps({
                    "instruction":instruction,
                    "step_num": step_idx  ,
                    "action_timestamp": action_timestamp,
                    "action": action,
                    "reward": reward,
                    "done": done,
                    "info": info,
                    "screenshot_file":obs['screenshot']
                    #"screenshot_file": f"step_{step_idx }_{action_timestamp}.png"
                },indent=4,ensure_ascii=False))
                f.write("\n")
            if done:
                logging.info("The episode is done.")
                break




if __name__=='__main__':
    from reqest1 import send_fake_req_7b,send_req
    from parse_action_try import parsing_response_to_pyautogui_code, parse_action_output

    parse_fn = parse_action_output

    agent = UITARSAgent( req_fn=send_req,
                         parse_fn=parse_fn,### 解析模型的输出
                         action2pyautogui_fn=parsing_response_to_pyautogui_code### 根据每个actiontype,attribute 分别写pyautogui
                         )##  依赖模型的  请求 ，解析,写pyautogui


    example_result_dir = './tmp516'
    if not  os.path.exists(example_result_dir):
        os.makedirs(example_result_dir)
    env = Env(screenshot_dir=example_result_dir)
    # Configure logging
    logging.basicConfig(filename=os.path.join(example_result_dir,'env_log.log'),
                        level=logging.INFO,
                        format='%(asctime)s %(levelname)s:%(message)s')
    instr="打开当前编辑器应用的设置菜单，设置快捷键"
    instr='打开浏览器'

    maxstep=10 # 单步的调成1
    outname='1'
    run_1example(instr,
                 maxstep,
                 outname,
                 logging,
                 env,
                 agent,
                 example_result_dir)