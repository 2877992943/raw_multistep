"""
系统提示  指令  +  历史 + current image


"""
from prompts import  get_prompt_uitars_raw
import base64
import re

def make_history_cell(h):
    return {
        "from": "gpt",
        "value": h,  # "history1 thought1",
        "loss_mask": 0
    }
def make_image_cell():
    return {
        "from": "human",
        "value": "<image> ",
        "loss_mask": 0
    }
def get_imgbase64_content(encoded_string=None,min_pixels=256,max_pixels=3300,cur_image=None):
    if cur_image:
        with open(cur_image, 'rb') as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        return {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "image": f"data:image/png;base64,{encoded_string}",
                    "min_pixels": min_pixels*28*28,
                    "max_pixels": max_pixels*28*28,

                }]}
    if encoded_string:
        return {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "image": f"data:image/png;base64,{encoded_string}",
                    #"min_pixels": min_pixels,
                   # "max_pixels": max_pixels,

                }]}

def get_his_content(history_response):
    return {
        "role": "assistant",
        "content": [{"type": "text",
                     "text": add_box_token(history_response)}]
    }


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
                updated_action = updated_action.replace(f"{coord_type}='({x},{y})'",
                                                        f"{coord_type}='<|box_start|>({x},{y})<|box_end|>'")
            processed_actions.append(updated_action)

        # Step 5: Reconstruct the final string
        final_string = suffix + "\n\n".join(processed_actions)
    else:
        final_string = input_string
    return final_string

def get_conversation_imgbase64(task,convs,png=None,encoded_string_img=None,base64flag=True):### 参考os-world agent 历史 处理
    """
    uitars
    message输入顺序： [系统提示词 + 任务] + [历史...] + 图
    convs提供顺序，
    其中内容,文本内容在里面，而图片内容在别处：  历史1 历史2...   图
    """
    #### 组装系统提示词+任务
    system_message_task = get_prompt_uitars_raw(task)
    messages = [
        {
            "role": "system",
            "content": [{"type": "text", "text": "You are a helpful assistant."}]
        },
        {
            "role": "user",
            "content": [{"type": "text", "text": system_message_task}]
        }]
    ######  历史1 历史2...  图
    for conv in convs:
        value=conv['value']
        lossmask=conv['loss_mask']
        if lossmask==0 and '<image>' not in value:# history
            history_response=value
            his={
                "role": "assistant",
                "content": [{"type": "text",
                             "text":  history_response}]
            }
            messages.append(his)
        if '<image>' in value:
            if not base64flag :
                #cur_image=os.path.join(inputImgdir,png)
                cur_image=png
                messages.append(
                    {
                    "role": "user",
                    "content": [{ "type": "image",
                                  "image": cur_image}]}
                )
            else:
                messages.append(get_imgbase64_content(encoded_string_img))
    return messages


def get_conversation_imgbase64_his(task,hisll,encoded_string_img=None,png=None):### 参考os-world agent 历史 处理
    """
    uitars
    message输入顺序： [系统提示词 + 任务] + [历史...] + 图
    convs提供顺序，
    其中内容,文本内容在里面，而图片内容在别处：  历史1 历史2...   图
    """
    #### 组装系统提示词+任务
    system_message_task = get_prompt_uitars_raw(task)
    messages = [
        {
            "role": "system",
            "content": [{"type": "text", "text": "You are a helpful assistant."}]
        },
        {
            "role": "user",
            "content": [{"type": "text", "text": system_message_task}]
        }]
    ######  历史1 历史2...  图
    for history_response in hisll:


        his={
                "role": "assistant",
                "content": [{"type": "text",
                             "text":  history_response}]
            }
        messages.append(his)

    ####
    assert png is not None or encoded_string_img is not None, "至少需要png encodeString一个变量不是 None"
    if png:
        messages.append(get_imgbase64_content(cur_image=png))
    else:
        if encoded_string_img:
            messages.append(get_imgbase64_content(encoded_string=encoded_string_img))

    return messages


def see_mess(message):
    for d in message:
        print(d)
        # if d['content'][0]['type']=='image':
        #     print(d['content'][0]['type'])
        # else:
        #     print(d)