import ast
import base64
import logging
import math
import re
import xml.etree.ElementTree as ET
from io import BytesIO
from typing import Dict, List
import json
#import backoff
import numpy as np
from PIL import Image
# from reqest1 import *
from requests.exceptions import SSLError
from make_message import see_mess
#from uitar_history_toy import get_prompt
from prompts import get_prompt_uitars_raw as get_prompt
# import openai
# from openai import OpenAI
# from google.api_core.exceptions import (
#     BadRequest,
#     InternalServerError,
#     InvalidArgument,
#     ResourceExhausted,
# )

# from mm_agents.accessibility_tree_wrap.heuristic_retrieve import (
#     filter_nodes,
# )
from prompts import (
    UITARS_ACTION_SPACE,
    UITARS_CALL_USR_ACTION_SPACE,
    UITARS_USR_PROMPT_NOTHOUGHT,
    UITARS_USR_PROMPT_THOUGHT,
    UITARS_NORMAL_ACTION_SPACE
)


logger = logging.getLogger("desktopenv.agent")

FINISH_WORD = "finished"
WAIT_WORD = "wait"
ENV_FAIL_WORD = "error_env"
CALL_USER = "call_user"

IMAGE_FACTOR = 28
MIN_PIXELS = 100 * 28 * 28
MAX_PIXELS = 16384 * 28 * 28
MAX_RATIO = 200

# pure_text_settings = ["a11y_tree"]
#
# attributes_ns_ubuntu = "https://accessibility.windows.example.org/ns/attributes"
# attributes_ns_windows = "https://accessibility.windows.example.org/ns/attributes"
# state_ns_ubuntu = "https://accessibility.ubuntu.example.org/ns/state"
# state_ns_windows = "https://accessibility.windows.example.org/ns/state"
# component_ns_ubuntu = "https://accessibility.ubuntu.example.org/ns/component"
# component_ns_windows = "https://accessibility.windows.example.org/ns/component"
# value_ns_ubuntu = "https://accessibility.ubuntu.example.org/ns/value"
# value_ns_windows = "https://accessibility.windows.example.org/ns/value"
# class_ns_windows = "https://accessibility.windows.example.org/ns/class"
# More namespaces defined in OSWorld, please check desktop_env/server/main.py


def prompt_block_userImg(modelType,cur_image=None,encoded_string=None):
    """
     modelType =['api','7b']

    """
    if cur_image!=None:### 提供了png格式 的图片
        # 读取图片文件并编码为base64
        with open(cur_image, 'rb') as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    if modelType=='7b':
        return {
            "role": "user",
            "content": [
                        #{ "type": "image","image": cur_image,}
                         {"type": "image", "image": f"data:image/png;base64,{encoded_string}"},

                         ]
                }
    elif modelType=='api':
        return {
                        "role": "user",
                        "content": [{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded_string}"}}]
                    }

def prompt_block_assiTxt(modelType,history_response):
    if modelType=='7b':
        return {
        "role": "assistant",
        "content": [{"type": "text",
                     "text": add_box_token(history_response)}]
        }
    elif modelType=='api':
        return {
                    "role": "assistant",
                    "content": [add_box_token(history_response)]
                }


#
# # 定义一个函数来解析每个 action
# def parse_action(action_str):
#     try:
#         # 解析字符串为 AST 节点
#         node = ast.parse(action_str, mode='eval')
#
#         # 确保节点是一个表达式
#         if not isinstance(node, ast.Expression):
#             raise ValueError("Not an expression")
#
#         # 获取表达式的主体
#         call = node.body
#
#         # 确保主体是一个函数调用
#         if not isinstance(call, ast.Call):
#             raise ValueError("Not a function call")
#
#         # 获取函数名
#         if isinstance(call.func, ast.Name):
#             func_name = call.func.id
#         elif isinstance(call.func, ast.Attribute):
#             func_name = call.func.attr
#         else:
#             func_name = None
#
#         # 获取关键字参数
#         kwargs = {}
#         for kw in call.keywords:
#             key = kw.arg
#             # 处理不同类型的值，这里假设都是常量
#             if isinstance(kw.value, ast.Constant):
#                 value = kw.value.value
#             elif isinstance(kw.value, ast.Str):  # 兼容旧版本 Python
#                 value = kw.value.s
#             else:
#                 value = None
#             kwargs[key] = value
#
#         return {
#             'function': func_name,
#             'args': kwargs
#         }
#
#     except Exception as e:
#         print(f"Failed to parse action '{action_str}': {e}")
#         return None
    
def escape_single_quotes(text):
    # 匹配未转义的单引号（不匹配 \\'）
    pattern = r"(?<!\\)'"
    return re.sub(pattern, r"\\'", text)

def round_by_factor(number: int, factor: int) -> int:
    """Returns the closest integer to 'number' that is divisible by 'factor'."""
    return round(number / factor) * factor


def ceil_by_factor(number: int, factor: int) -> int:
    """Returns the smallest integer greater than or equal to 'number' that is divisible by 'factor'."""
    return math.ceil(number / factor) * factor


def floor_by_factor(number: int, factor: int) -> int:
    """Returns the largest integer less than or equal to 'number' that is divisible by 'factor'."""
    return math.floor(number / factor) * factor

def linear_resize(
    height: int, width: int, factor: int = IMAGE_FACTOR, min_pixels: int = MIN_PIXELS, max_pixels: int = MAX_PIXELS
) -> tuple[int, int]:
    if width * height > max_pixels:
        """
        如果图片超过/低于像素限制，则计算一个缩放因子resize_factor，使图片的像素数缩小到等于或小于max_pixels。这个缩放因子是通过开平方根计算的，确保纵横比保持不变,这样原始的相对坐标可以不经转换直接复用
        """
        resize_factor = math.sqrt(max_pixels / (width * height))
        width, height = int(width * resize_factor), int(height * resize_factor)
    if width * height < min_pixels:
        resize_factor = math.sqrt(min_pixels / (width * height))
        width, height = math.ceil(width * resize_factor), math.ceil(height * resize_factor)

    return height, width 

def smart_resize(
    height: int, width: int, factor: int = IMAGE_FACTOR, min_pixels: int = MIN_PIXELS, max_pixels: int = MAX_PIXELS
) -> tuple[int, int]:
    """
    Rescales the image so that the following conditions are met:

    1. Both dimensions (height and width) are divisible by 'factor'.

    2. The total number of pixels is within the range ['min_pixels', 'max_pixels'].

    3. The aspect ratio of the image is maintained as closely as possible.
    """
    if max(height, width) / min(height, width) > MAX_RATIO:
        raise ValueError(
            f"absolute aspect ratio must be smaller than {MAX_RATIO}, got {max(height, width) / min(height, width)}"
        )
    h_bar = max(factor, round_by_factor(height, factor))
    w_bar = max(factor, round_by_factor(width, factor))
    if h_bar * w_bar > max_pixels:
        beta = math.sqrt((height * width) / max_pixels)
        h_bar = floor_by_factor(height / beta, factor)
        w_bar = floor_by_factor(width / beta, factor)
    elif h_bar * w_bar < min_pixels:
        beta = math.sqrt(min_pixels / (height * width))
        h_bar = ceil_by_factor(height * beta, factor)
        w_bar = ceil_by_factor(width * beta, factor)
    return h_bar, w_bar

# def parse_action_to_structure_output(text, factor, origin_resized_height, origin_resized_width, model_type, max_pixels=16384*28*28, min_pixels=100*28*28):
#     text = text.strip()
#     if model_type == "qwen25vl":
#         smart_resize_height, smart_resize_width = smart_resize(origin_resized_height, origin_resized_width, factor=IMAGE_FACTOR, min_pixels=min_pixels, max_pixels=max_pixels)
#
#     # 正则表达式匹配 Action 字符串
#     if text.startswith("Thought:"):
#         thought_pattern = r"Thought: (.+?)(?=\s*Action:|$)"
#         thought_hint = "Thought: "
#     elif text.startswith("Reflection:"):
#         thought_pattern = r"Reflection: (.+?)Action_Summary: (.+?)(?=\s*Action:|$)"
#         thought_hint = "Reflection: "
#     elif text.startswith("Action_Summary:"):
#         thought_pattern = r"Action_Summary: (.+?)(?=\s*Action:|$)"
#         thought_hint = "Action_Summary: "
#     else:
#         thought_pattern = r"Thought: (.+?)(?=\s*Action:|$)"
#         thought_hint = "Thought: "
#     reflection, thought = None, None
#     thought_match = re.search(thought_pattern, text, re.DOTALL)
#     if thought_match:
#         if len(thought_match.groups()) == 1:
#             thought = thought_match.group(1).strip()
#         elif len(thought_match.groups()) == 2:
#             thought = thought_match.group(2).strip()
#             reflection = thought_match.group(1).strip()
#     assert "Action:" in text
#     action_str = text.split("Action:")[-1]
#
#     tmp_all_action = action_str.split("\n\n")
#     all_action = []
#     for action_str in tmp_all_action:
#         if "type(content" in action_str:
#             # 正则表达式匹配 content 中的字符串并转义单引号
#             def escape_quotes(match):
#                 content = match.group(1)  # 获取 content 的值
#                 return content
#
#             # 使用正则表达式进行替换
#             pattern = r"type\(content='(.*?)'\)"  # 匹配 type(content='...')
#             content = re.sub(pattern, escape_quotes, action_str)
#
#             # 处理字符串
#             action_str = escape_single_quotes(content)
#             action_str = "type(content='" + action_str + "')"
#         all_action.append(action_str)
#
#     parsed_actions = [parse_action(action.replace("\n","\\n").lstrip()) for action in all_action]
#     actions = []
#     for action_instance, raw_str in zip(parsed_actions, all_action):
#         if action_instance == None:
#             print(f"Action can't parse: {raw_str}")
#             raise ValueError(f"Action can't parse: {raw_str}")
#         action_type = action_instance["function"]
#         params = action_instance["args"]
#
#         # import pdb; pdb.set_trace()
#         action_inputs = {}
#         for param_name, param in params.items():
#             if param == "": continue
#             param = param.lstrip()  # 去掉引号和多余的空格
#             # 处理start_box或者end_box参数格式 '<bbox>x1 y1 x2 y2</bbox>'
#             action_inputs[param_name.strip()] = param
#
#             if "start_box" in param_name or "end_box" in param_name:
#                 ori_box = param
#                 # Remove parentheses and split the string by commas
#                 numbers = ori_box.replace("(", "").replace(")", "").split(",")
#
#                 # Convert to float and scale by 1000
#                 # Qwen2.5vl output absolute coordinates, qwen2vl output relative coordinates
#                 if model_type == "qwen25vl":
#                     float_numbers = []
#                     for num_idx, num in enumerate(numbers):
#                         num = float(num)
#                         if (num_idx + 1) % 2 == 0:
#                             float_numbers.append(float(num/smart_resize_height))
#                         else:
#                             float_numbers.append(float(num/smart_resize_width))
#                 else:
#                     float_numbers = [float(num) / factor for num in numbers]
#
#                 if len(float_numbers) == 2:
#                     float_numbers = [float_numbers[0], float_numbers[1], float_numbers[0], float_numbers[1]]
#                 action_inputs[param_name.strip()] = str(float_numbers)
#
#         # import pdb; pdb.set_trace()
#         actions.append({
#             "reflection": reflection,
#             "thought": thought,
#             "action_type": action_type,
#             "action_inputs": action_inputs,
#             "text": text
#         })
#     return actions

# def parsing_response_to_pyautogui_code(responses, image_height: int, image_width:int, input_swap:bool=True) -> str:
#     '''
#     将M模型的输出解析为OSWorld中的action，生成pyautogui代码字符串
#     参数:
#         response: 包含模型输出的字典，结构类似于：
#         {
#             "action_type": "hotkey",
#             "action_inputs": {
#                 "hotkey": "v ctrl",
#                 "start_box": None,
#                 "end_box": None
#             }
#         }
#     返回:
#         生成的pyautogui代码字符串
#     '''
#
#     pyautogui_code = f"import pyautogui\nimport time\n"
#
#     image_width=1
#     image_height=1
#
#
#     if isinstance(responses, dict):
#         responses = [responses]
#     for response_id, response in enumerate(responses):#### 遍历 一次预测中的  每一个 actiondict
#         ##### 换成 action_type
#         if 'action' in response:
#             response['action_type']=response['action']
#         if not 'action_inputs' in response:
#             response['action_inputs']=response
#
#         #####
#         if "observation" in response:
#             observation = response["observation"]
#         else:
#             observation = ""
#
#         if "thought" in response:
#             thought = response["thought"]
#         else:
#             thought = ""
#
#         if response_id == 0:
#             pyautogui_code += f"'''\nObservation:\n{observation}\n\nThought:\n{thought}\n'''\n"
#         else:
#             pyautogui_code += f"\ntime.sleep(1)\n"
#
#         action_dict = response
#         action_type = action_dict.get("action_type")
#         action_inputs = action_dict.get("action_inputs", {})
#
#         if action_type == "hotkey":
#             # Parsing hotkey action
#             if "key" in action_inputs:
#                 hotkey = action_inputs.get("key", "")
#             else:
#                 hotkey = action_inputs.get("hotkey", "")
#
#             if hotkey == "arrowleft":
#                 hotkey = "left"
#
#             elif hotkey == "arrowright":
#                 hotkey = "right"
#
#             elif hotkey == "arrowup":
#                 hotkey = "up"
#
#             elif hotkey == "arrowdown":
#                 hotkey = "down"
#
#             if hotkey:
#                 # Handle other hotkeys
#                 keys = hotkey.split()  # Split the keys by space
#                 convert_keys = []
#                 for key in keys:
#                     if key == "space":
#                         key = ' '
#                     convert_keys.append(key)
#                 pyautogui_code += f"\npyautogui.hotkey({', '.join([repr(k) for k in convert_keys])})"
#
#         elif action_type == "press":
#             # Parsing press action
#             if "key" in action_inputs:
#                 key_to_press = action_inputs.get("key", "")
#             else:
#                 key_to_press = action_inputs.get("press", "")
#
#             if hotkey == "arrowleft":
#                 hotkey = "left"
#
#             elif hotkey == "arrowright":
#                 hotkey = "right"
#
#             elif hotkey == "arrowup":
#                 hotkey = "up"
#
#             elif hotkey == "arrowdown":
#                 hotkey = "down"
#
#             elif hotkey == "space":
#                 hotkey = " "
#
#             if key_to_press:
#                 # Simulate pressing a single key
#                 pyautogui_code += f"\npyautogui.press({repr(key_to_press)})"
#
#         elif action_type == "keyup":
#             key_to_up = action_inputs.get("key", "")
#             pyautogui_code += f"\npyautogui.keyUp({repr(key_to_up)})"
#
#         elif action_type == "keydown":
#             key_to_down = action_inputs.get("key", "")
#             pyautogui_code += f"\npyautogui.keyDown({repr(key_to_down)})"
#
#         elif action_type == "type":
#             # Parsing typing action using clipboard
#             content = action_inputs.get("content", "")
#             content = escape_single_quotes(content)
#             stripped_content = content
#             if content.endswith("\n") or content.endswith("\\n"):
#                 stripped_content = stripped_content.rstrip("\\n").rstrip("\n")
#             if content:
#                 if input_swap:
#                     pyautogui_code += f"\nimport pyperclip"
#                     pyautogui_code += f"\npyperclip.copy('{stripped_content}')"
#                     pyautogui_code += f"\npyautogui.hotkey('ctrl', 'v')"
#                     pyautogui_code += f"\ntime.sleep(0.5)\n"
#                     if content.endswith("\n") or content.endswith("\\n"):
#                         pyautogui_code += f"\npyautogui.press('enter')"
#                 else:
#                     pyautogui_code += f"\npyautogui.write('{stripped_content}', interval=0.1)"
#                     pyautogui_code += f"\ntime.sleep(0.5)\n"
#                     if content.endswith("\n") or content.endswith("\\n"):
#                         pyautogui_code += f"\npyautogui.press('enter')"
#
#
#         elif action_type in ["drag", "select"]:
#             # Parsing drag or select action based on start and end_boxes
#             start_box = action_inputs.get("start_box")
#             end_box = action_inputs.get("end_box")
#             if type(start_box)!=str:start_box=str(start_box)
#             if type(end_box)!=str:end_box=str(end_box)
#             if start_box and end_box:
#
#                 startll=eval(start_box)
#                 if len(startll)==4:
#                     x1, y1, x2, y2 = eval(start_box)  # Assuming box is in [x1, y1, x2, y2]
#                 if len(startll)==2:
#                     x1, y1 = eval(start_box)
#                     x2 = x1
#                     y2 = y1
#                 #####
#                 sx = round(float((x1 + x2) / 2) * image_width, 3)
#                 sy = round(float((y1 + y2) / 2) * image_height, 3)
#
#                 ####end
#                 endll=eval(end_box)
#                 if len(endll)==4:
#                     x1, y1, x2, y2 = eval(end_box)  # Assuming box is in [x1, y1, x2, y2]
#                 if len(endll)==2:
#                     x1, y1 = eval(end_box)
#                     x2 = x1
#                     y2 = y1
#                 #####
#                 ex = round(float((x1 + x2) / 2) * image_width, 3)
#                 ey = round(float((y1 + y2) / 2) * image_height, 3)
#                 ###
#                 sx=int(sx)
#                 sy=int(sy)
#                 ex=int(ex)
#                 ey=int(ey)
#                 pyautogui_code += (
#                     f"\npyautogui.moveTo({sx}, {sy})\n"
#                     f"\npyautogui.dragTo({ex}, {ey}, duration=1.0)\n"
#                 )
#
#         elif action_type == "scroll":
#             # Parsing scroll action
#             start_box = action_inputs.get("start_box")
#             if start_box:
#                 x1, y1, x2, y2 = eval(start_box)  # Assuming box is in [x1, y1, x2, y2]
#                 x = round(float((x1 + x2) / 2) * image_width, 3)
#                 y = round(float((y1 + y2) / 2) * image_height, 3)
#
#                 # # 先点对应区域，再滚动
#                 # pyautogui_code += f"\npyautogui.click({x}, {y}, button='left')"
#             else:
#                 x = None
#                 y = None
#             direction = action_inputs.get("direction", "")
#
#             if x == None:
#                 if "up" in direction.lower():
#                     pyautogui_code += f"\npyautogui.scroll(5)"
#                 elif "down" in direction.lower():
#                     pyautogui_code += f"\npyautogui.scroll(-5)"
#             else:
#                 if "up" in direction.lower():
#                     pyautogui_code += f"\npyautogui.scroll(5, x={x}, y={y})"
#                 elif "down" in direction.lower():
#                     pyautogui_code += f"\npyautogui.scroll(-5, x={x}, y={y})"
#
#         elif action_type in ["click", "left_single", "left_double", "right_single", "hover"]:
#             # Parsing mouse click actions
#             start_box = action_inputs.get("start_box")
#             start_box = str(start_box)
#             if start_box:
#                 start_box = eval(start_box)
#                 if len(start_box) == 4:
#                     x1, y1, x2, y2 = start_box  # Assuming box is in [x1, y1, x2, y2]
#                 elif len(start_box) == 2:
#                     x1, y1 = start_box
#                     x2 = x1
#                     y2 = y1
#                 #x = round(float((x1 + x2) / 2) * image_width, 3)
#                 #y = round(float((y1 + y2) / 2) * image_height, 3)
#                 x = round(float((x1 + x2) / 2) , 3)
#                 y = round(float((y1 + y2) / 2)  , 3)
#                 x=int(x);y=int(y)
#                 if action_type == "left_single" or action_type == "click":
#                     pyautogui_code += f"\npyautogui.click({x}, {y}, button='left')"
#                 elif action_type == "left_double":
#                     pyautogui_code += f"\npyautogui.doubleClick({x}, {y}, button='left')"
#                 elif action_type == "right_single":
#                     pyautogui_code += f"\npyautogui.click({x}, {y}, button='right')"
#                 elif action_type == "hover":
#                     pyautogui_code += f"\npyautogui.moveTo({x}, {y})"
#
#         elif action_type in ["finished"]:
#             pyautogui_code = f"DONE"
#
#         else:
#             pyautogui_code += f"\n# Unrecognized action type: {action_type}"
#
#     return pyautogui_code

def add_box_token(input_string):
    # Step 1: Split the string into individual actions
    if "Action: " in input_string and "start_box=" in input_string:
        suffix = input_string.split("Action: ")[0] + "Action: "
        actions = input_string.split("Action: ")[1:]
        processed_actions = []
        for action in actions:
            action = action.strip()
            # Step 2: Extract coordinates (start_box or end_box) using regex
            coordinates = re.findall(r"(start_box|end_box)='\((\d+),\s*(\d+)\)'", action)
            
            updated_action = action  # Start with the original action
            for coord_type, x, y in coordinates:
                # Convert x and y to integers
                updated_action = updated_action.replace(f"{coord_type}='({x},{y})'", f"{coord_type}='<|box_start|>({x},{y})<|box_end|>'")
            processed_actions.append(updated_action)
        
        # Step 5: Reconstruct the final string
        final_string = suffix + "\n\n".join(processed_actions)
    else:
        final_string = input_string
    return final_string

def pil_to_base64(image):
    buffer = BytesIO()
    image.save(buffer, format="PNG")  # 你可以改成 "JPEG" 等格式
    return base64.b64encode(buffer.getvalue()).decode("utf-8")

def linearize_accessibility_tree(accessibility_tree, platform="ubuntu"):

    if platform == "ubuntu":
        _attributes_ns = attributes_ns_ubuntu
        _state_ns = state_ns_ubuntu
        _component_ns = component_ns_ubuntu
        _value_ns = value_ns_ubuntu
    elif platform == "windows":
        _attributes_ns = attributes_ns_windows
        _state_ns = state_ns_windows
        _component_ns = component_ns_windows
        _value_ns = value_ns_windows
    else:
        raise ValueError("Invalid platform, must be 'ubuntu' or 'windows'")

    filtered_nodes = filter_nodes(ET.fromstring(accessibility_tree), platform)
    linearized_accessibility_tree = [
        "tag\tname\ttext\tclass\tdescription\tposition (top-left x&y)\tsize (w&h)"
    ]

    # Linearize the accessibility tree nodes into a table format
    for node in filtered_nodes:
        if node.text:
            text = (
                node.text
                if '"' not in node.text
                else '"{:}"'.format(node.text.replace('"', '""'))
            )

        elif node.get("{{{:}}}class".format(class_ns_windows), "").endswith(
            "EditWrapper"
        ) and node.get("{{{:}}}value".format(_value_ns)):
            node_text = node.get("{{{:}}}value".format(_value_ns), "")
            text = (
                node_text
                if '"' not in node_text
                else '"{:}"'.format(node_text.replace('"', '""'))
            )
        else:
            text = '""'

        linearized_accessibility_tree.append(
            "{:}\t{:}\t{:}\t{:}\t{:}\t{:}\t{:}".format(
                node.tag,
                node.get("name", ""),
                text,
                (
                    node.get("{{{:}}}class".format(_attributes_ns), "")
                    if platform == "ubuntu"
                    else node.get("{{{:}}}class".format(class_ns_windows), "")
                ),
                node.get("{{{:}}}description".format(_attributes_ns), ""),
                node.get("{{{:}}}screencoord".format(_component_ns), ""),
                node.get("{{{:}}}size".format(_component_ns), ""),
            )
        )

    return "\n".join(linearized_accessibility_tree)

def trim_accessibility_tree(linearized_accessibility_tree, max_tokens):
    # enc = tiktoken.encoding_for_model("gpt-4")
    # tokens = enc.encode(linearized_accessibility_tree)
    # if len(tokens) > max_tokens:
    #     linearized_accessibility_tree = enc.decode(tokens[:max_tokens])
    #     linearized_accessibility_tree += "[...]\n"
    return linearized_accessibility_tree

# def parse_action_output(output_text):
#     # 提取Thought部分
#     thought_match = re.search(r'Thought:(.*?)\nAction:', output_text, re.DOTALL)
#     thought = thought_match.group(1).strip() if thought_match else ""
#
#     # 提取Action部分
#     action_match = re.search(r'Action:(.*?)(?:\n|$)', output_text, re.DOTALL)
#     action_text = action_match.group(1).strip() if action_match else ""
#
#     #print(thought)
#     #print(617,action_text)
#     parsed_act=parse_action7b(action_text)
#
#     # 初始化结果字典
#     result = {
#         "thought": thought,
#         "action": "",
#         "key": None,
#         "content": None,
#         "start_box": None,
#         "end_box": None,
#         "direction": None
#     }
#
#     result['action']=parsed_act['action']
#     params=parsed_act['params']
#     if 'start_box' in params:
#         result['start_box_int']=params['start_box']
#         result['start_box']=params['start_box'] #[v/1000. for v in params['start_box']]
#     if 'end_box' in params:
#         result['end_box_int'] = params['end_box']
#         result['end_box'] =  params['end_box']#[v / 1000. for v in params['end_box']]
#     if 'direction' in params:
#         result['direction']=params['direction']
#     if 'content' in params:
#         result['content']=params['content']
#     if 'key' in params:
#         result['key']=params['key']
#     return json.dumps(result, ensure_ascii=False, indent=2)




class UITARSAgent:
    def __init__(
        self,
        num_history_use_num=3,#### history text number,for oom issue
        platform="ubuntu",
        action_space="pyautogui",
        observation_type="screenshot",
        # observation_type can be in ["screenshot", "a11y_tree", "screenshot_a11y_tree", "som"]
        max_trajectory_length=10,
        #a11y_tree_max_tokens=10000,
        model_type="qwen25vl",
            req_fn=None,
            parse_fn=None,
            action2pyautogui_fn=None,
        runtime_conf: dict = {
            "infer_mode": "qwen25vl_normal",
            "prompt_style": "qwen25vl_normal",
            "input_swap": False,#True,
            "language": "Chinese",
            "history_n": 1,#5  history image number
            "max_pixels": 16384*28*28,
            "min_pixels": 100*28*28,
            "callusr_tolerance": 3,
            "temperature": 0.0,
            "top_k": -1,
            "top_p": 0.9,
            "max_tokens": 500

        }
    ):
        self.platform = platform
        self.action_space = action_space
        self.observation_type = observation_type
        self.max_trajectory_length = max_trajectory_length
        #self.a11y_tree_max_tokens = a11y_tree_max_tokens
        self.model_type = model_type
        self.runtime_conf = runtime_conf
        self.vlm='fake model api'
        #### depand on 模型
        self.send_req=req_fn
        self.parse_fn=parse_fn## 解析模型输出
        self.parsing_response_to_pyautogui_code=action2pyautogui_fn #将action ,attribute 写pyautogui
        # self.vlm = OpenAI(
        #     base_url="http://127.0.0.1:8000/v1",
        #     api_key="empty",
        # ) # should replace with your UI-TARS server api
        self.temperature = self.runtime_conf["temperature"]
        self.top_k = self.runtime_conf["top_k"]
        self.top_p = self.runtime_conf["top_p"]
        self.max_tokens = self.runtime_conf["max_tokens"]
        self.infer_mode = self.runtime_conf["infer_mode"]
        self.prompt_style = self.runtime_conf["prompt_style"]
        self.input_swap = self.runtime_conf["input_swap"]
        self.language = self.runtime_conf["language"]
        self.max_pixels = self.runtime_conf["max_pixels"]
        self.min_pixels = self.runtime_conf["min_pixels"]
        self.callusr_tolerance = self.runtime_conf["callusr_tolerance"]

        self.thoughts = []
        self.actions = []
        self.observations = []
        self.history_images = []
        self.history_responses = []
        self.history_respons_use_num=num_history_use_num
        
        self.prompt_action_space = UITARS_ACTION_SPACE
        self.action_parse_res_factor = 1000
        if self.infer_mode == "qwen2vl_user":
            self.prompt_action_space = UITARS_CALL_USR_ACTION_SPACE
        elif self.infer_mode == "qwen25vl_normal":
            self.prompt_action_space = UITARS_NORMAL_ACTION_SPACE
    
        self.prompt_template = UITARS_USR_PROMPT_THOUGHT
        
        if self.prompt_style == "qwen2vl_user" or self.prompt_style == "qwen25vl_normal":
            self.prompt_template = UITARS_USR_PROMPT_THOUGHT

        elif self.prompt_style == "qwen2vl_no_thought":
            self.prompt_template = UITARS_USR_PROMPT_NOTHOUGHT

        
        if "history_n" in self.runtime_conf:
            self.history_n = self.runtime_conf["history_n"]
        else:
            self.history_n = 5
        
        self.cur_callusr_count = 0

    def predict(
        self, instruction: str, obs: Dict, last_action_after_obs: Dict = None
    ) -> List:
        """
        Predict the next action(s) based on the current observation.
        """

        # Append trajectory
        # print(len(self.observations), len(self.actions), len(self.actions))
        assert len(self.observations) == len(self.actions) and len(self.actions) == len(
            self.thoughts
        ), "The number of observations and actions should be the same."

        if len(self.observations) > self.max_trajectory_length:
            if self.max_trajectory_length == 0:
                _observations = []
                _actions = []
                _thoughts = []
            else:
                _observations = self.observations[-self.max_trajectory_length :]
                _actions = self.actions[-self.max_trajectory_length :]
                _thoughts = self.thoughts[-self.max_trajectory_length :]
        else:
            _observations = self.observations
            _actions = self.actions
            _thoughts = self.thoughts

        # for previous_obs, previous_action, previous_thought in zip(
        #     _observations, _actions, _thoughts
        # ):
        #     # {{{1
        #     if self.observation_type == "screenshot_a11y_tree":
        #         _screenshot = previous_obs["screenshot"]
        #         _linearized_accessibility_tree = previous_obs["accessibility_tree"]
        #
        #     else:
        #         raise ValueError(
        #             "Invalid observation_type type: " + self.observation_type
        #         )  # 1}}}

        self.history_images.append(obs["screenshot"])#### 第一个元素是  新传进来的图片
        new_image_input=obs["screenshot"]
        new_image_input_pil=self.img2PIL(new_image_input)

        if self.observation_type in ["screenshot", "screenshot_a11y_tree"]:
            base64_image = obs["screenshot"]
            # try:
            #     linearized_accessibility_tree = (
            #         linearize_accessibility_tree(
            #             accessibility_tree=obs["accessibility_tree"],
            #             platform=self.platform,
            #         )
            #         if self.observation_type == "screenshot_a11y_tree"
            #         else None
            #     )
            # except:
                #linearized_accessibility_tree = None
            # logger.debug("LINEAR AT: %s", linearized_accessibility_tree)

            # if linearized_accessibility_tree:
            #     linearized_accessibility_tree = trim_accessibility_tree(
            #         linearized_accessibility_tree, self.a11y_tree_max_tokens
            #     )
            #
            # if self.observation_type == "screenshot_a11y_tree":
            #     self.observations.append(
            #         {
            #             "screenshot": base64_image,
            #             "accessibility_tree": linearized_accessibility_tree,
            #         }
            #     )
            #else:
            if 1:
                self.observations.append(
                    {"screenshot": base64_image, "accessibility_tree": None}
                )

        else:
            raise ValueError(
                "Invalid observation_type type: " + self.observation_type
            )  # 1}}}
        
        # if self.infer_mode == "qwen2vl_user" or self.infer_mode == "qwen25vl_normal":
        #     user_prompt = self.prompt_template.format(
        #         instruction=instruction,
        #         action_space=self.prompt_action_space,
        #         language=self.language
        #     )

        # elif self.infer_mode == "qwen2vl_no_thought":
        #     user_prompt = self.prompt_template.format(
        #         instruction=instruction
        #     )

        if len(self.history_images) > self.history_n:
            self.history_images = self.history_images[-self.history_n:]### 历史图片是倒数的5个


        ###########
        # ### 历史图片
        messages, images = [], []
        if isinstance(self.history_images, bytes):
            self.history_images = [self.history_images]
        elif isinstance(self.history_images, np.ndarray):
            self.history_images = list(self.history_images)
        elif isinstance(self.history_images, list):
            pass
        else:
            raise TypeError(f"Unidentified images type: {type(self.history_images)}")

        for turn, image in enumerate(self.history_images):
            if len(images) >= self.history_n:### 如果历史图片超过5个
                break
            try:
                #image = Image.open(BytesIO(image))
                image=Image.open(image)
            except Exception as e:
                raise RuntimeError(f"Error opening image: {e}")

            if image.width * image.height > self.max_pixels:
                """
                如果图片超过/低于像素限制，则计算一个缩放因子resize_factor，使图片的像素数缩小到等于或小于max_pixels。这个缩放因子是通过开平方根计算的，确保纵横比保持不变,这样原始的相对坐标可以不经转换直接复用
                """
                resize_factor = math.sqrt(self.max_pixels / (image.width * image.height))
                width, height = int(image.width * resize_factor), int(image.height * resize_factor)
                image = image.resize((width, height))
            if image.width * image.height < self.min_pixels:
                resize_factor = math.sqrt(self.min_pixels / (image.width * image.height))
                width, height = math.ceil(image.width * resize_factor), math.ceil(image.height * resize_factor)
                image = image.resize((width, height))

            if image.mode != "RGB":
                image = image.convert("RGB")

           # img_png=self.history_images[turn]
            images.append(image)### PIL 类型


        #############
        ## 历史 act thought
        print(get_prompt(instruction))
        messages = [
            {
                "role": "system",
                "content": [{"type": "text", "text": "You are a helpful assistant."}]
            },
            {
                "role": "user",
                "content": [{"type": "text", "text": get_prompt(instruction)}]
            }
        ]
        
        image_num = 0
        self.history_responses_limituse=self.history_responses[-self.history_respons_use_num:]### 全部输入 历史 太长 OOM
        if len(self.history_responses) > 0:
            print('current history repons...',self.history_responses)
            #for history_idx, history_response in enumerate(self.history_responses):
            for history_idx, history_response in enumerate(self.history_responses_limituse):
                if False:
                    # send at most history_n images to the model 只保存n个历史图片
                    if history_idx + self.history_n > len(self.history_responses):

                        cur_image = images[image_num]
                        encoded_string = pil_to_base64(cur_image)
                        messages.append(
                            prompt_block_userImg('7b', encoded_string=encoded_string)
                        #     {
                        #     "role": "user",
                        #     "content": [{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded_string}"}}]
                        # }
                        )
                        image_num += 1
                    
                messages.append(
                    prompt_block_assiTxt('7b',history_response)
                #     {
                #     "role": "assistant",
                #     "content": [add_box_token(history_response)]
                # }
                )

            #cur_image = images[image_num]
            cur_image = new_image_input_pil
            encoded_string = pil_to_base64(cur_image)
            messages.append(
                prompt_block_userImg('7b',encoded_string=encoded_string)
            #     {
            #     "role": "user",
            #     "content": [{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded_string}"}}]
            # }
            )
            #image_num += 1
        
        else:
            #cur_image = images[image_num]## png
            cur_image=new_image_input_pil
            encoded_string = pil_to_base64(cur_image)
            messages.append(
                prompt_block_userImg('7b', encoded_string=encoded_string)
            #     {
            #     "role": "user",
            #     "content": [{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded_string}"}}]
            # }
            )
            image_num += 1

        #######
        # 尝试 3次 预测和解析结果
        try_times = 3
        origin_resized_height = images[-1].height
        origin_resized_width = images[-1].width
        temperature = self.temperature
        top_k = self.top_k

        #see_mess(messages)
        #print(done)
        while True:
            if try_times <= 0:
                print(f"Reach max retry times to fetch response from client, as error flag.")
                return "client error", ["DONE"], []
            try:
                ##### 推理预测
                # response = self.vlm.chat.completions.create(
                #     model="ui-tars",
                #     messages=messages,
                #     frequency_penalty=1,
                #     max_tokens=self.max_tokens,
                #     temperature=temperature,
                #     top_k=top_k,
                #     top_p=self.top_p
                # )
                # # print(response.choices[0].message.content)
                # prediction = response.choices[0].message.content.strip()
                # prediction = response[0]["prediction"].strip()

                response=self.send_req(messages)
                prediction=response
                if False:
                    response="Thought: 我看到界面右上角\nAction: click(start_box=<bbox>970 15 970 15</bbox>"## api
                    prediction="Thought: 我看到界面右上角\nAction: click(start_box=<bbox>970 15 970 15</bbox>"### api

            except Exception as e:
                response=None
                print(f"Error when fetching response from client, with response: {response}")
                prediction = None
                try_times -= 1
            
            try:
                # parsed_responses = parse_action_to_structure_output(
                #     prediction,
                #     self.action_parse_res_factor,
                #     origin_resized_height,
                #     origin_resized_width,
                #     self.model_type,
                #     self.max_pixels,
                #     self.min_pixels
                # )
                o=self.parse_fn(prediction)
                o=json.loads(o);
                break#### 解析成功就退出
            except Exception as e:
                print(f"Error when parsing response from client, with response: {response}")
                # If fail to parse the model response, we use sampling parameters to avoid it
                prediction = None
                try_times -= 1
                temperature = 1
                top_k = -1
                
        if prediction is None:
            return "client error", ["DONE"]

        self.history_responses.append(prediction)##### 累加历史
        self.thoughts.append(prediction)

        ##############
        # 开始解析结果  执行
        try:
            # parsed_responses = parse_action_to_structure_output(
            #     prediction,
            #     self.action_parse_res_factor,
            #     origin_resized_height,
            #     origin_resized_width,
            #     self.model_type,
            #     self.max_pixels,
            #     self.min_pixels
            # )
            o = self.parse_fn(prediction)
            o = json.loads(o)
            print(996,'parsed response',o)
        except Exception as e:
            print(f"Parsing action error: {prediction}, with error:\n{e}")
            return f"Parsing action error: {prediction}, with error:\n{e}", ["DONE"]

        actions = []
        last_image = Image.open(self.history_images[-1])
        obs_image_height = last_image.height
        obs_image_width = last_image.width
        parsed_responses=[o] if type(o)!=list else o

        for parsed_response in parsed_responses:
            if "action_type" in parsed_response:

                if parsed_response["action_type"] == FINISH_WORD:
                    self.actions.append(actions)

                    return prediction, ["DONE"]
                
                elif parsed_response["action_type"] == WAIT_WORD:
                    self.actions.append(actions)
                    return prediction, ["WAIT"]
                
                elif parsed_response["action_type"] == ENV_FAIL_WORD:
                    self.actions.append(actions)
                    return prediction, ["FAIL"]

                elif parsed_response["action_type"] == CALL_USER:
                    if self.callusr_tolerance > self.cur_callusr_count:
                        self.actions.append(actions)
                        self.cur_callusr_count += 1
                        return prediction, ["WAIT"]
                    else:
                        self.actions.append(actions)
                        return prediction, ["FAIL"]
            
            pyautogui_code = self.parsing_response_to_pyautogui_code(
                parsed_response,
                obs_image_height,
                obs_image_width,
                self.input_swap
            )
            actions.append(pyautogui_code)

        self.actions.append(actions)## actions=[]

        if len(self.history_responses) >= self.max_trajectory_length:
            # Default to FAIL if exceed max steps
            actions = ["FAIL"]
        print('1044 累计的历史',self.history_images,self.history_responses,self.actions)
        return prediction, actions## 返回当前预测的

    #
    # @backoff.on_exception(
    #     backoff.constant,
    #     # here you should add more model exceptions as you want,
    #     # but you are forbidden to add "Exception", that is, a common type of exception
    #     # because we want to catch this kind of Exception in the outside to ensure each example won't exceed the time limit
    #     (
    #         # General exceptions
    #         SSLError,
    #         # OpenAI exceptions
    #         openai.RateLimitError,
    #         openai.BadRequestError,
    #         openai.InternalServerError,
    #         # Google exceptions
    #         InvalidArgument,
    #         ResourceExhausted,
    #         InternalServerError,
    #         BadRequest,
    #         # Groq exceptions
    #         # todo: check
    #     ),
    #     interval=30,
    #     max_tries=10,
    # )
    #
    def reset(self, runtime_logger=None):
        print('reset agent')
        self.thoughts = []
        self.actions = []
        self.observations = []
        self.history_images = []
        self.history_responses = []


    def img2PIL(self,png):
        image=Image.open(png)
        if image.mode != "RGB":
            image = image.convert("RGB")
        return image

