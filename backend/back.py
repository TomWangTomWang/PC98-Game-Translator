import gradio as gr
import torch
import os
import glob
import time
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info
import uvicorn
from fastapi import FastAPI
import threading

# -------------------------------
# 模型与处理器加载
# -------------------------------
model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
    "/home/tomwang/models/Qwen2.5-VL-3B-Instruct",
    torch_dtype="auto",
    device_map="auto",
    local_files_only=True  # 仅从本地加载
)

processor = AutoProcessor.from_pretrained(
    "/home/tomwang/models/Qwen2.5-VL-3B-Instruct",
    local_files_only=True  # 仅从本地加载
)

# -------------------------------
# 工具函数：获取最新截图
# -------------------------------
def get_latest_image(image_dir):
    """
    获取指定目录下最新修改的PNG图片文件。
    """
    image_files = glob.glob(os.path.join(image_dir, "*.png"))
    if not image_files:
        return None
    latest_image_file = max(image_files, key=os.path.getmtime)
    return latest_image_file

# -------------------------------
# 翻译函数：自动处理最新截图并进行推理
# -------------------------------
def process_image_and_text():
    """
    从预设目录自动获取最新截图，并将图片中的日文翻译成中文。
    如果未找到截图，返回错误信息；推理过程中发生异常也会返回错误提示。
    """
    image_dir = "/mnt/d/Cursor/sp/temppic"  # 截图所在目录（WSL下可访问Windows共享目录）
    image_path = get_latest_image(image_dir)
    if not image_path:
        return "没有找到截图。"
    
    # 定义翻译提示词
    text_prompt = "将图片中的日文翻译成中文,只输出中文并且必须输出中文。"
    
    # 构建消息格式
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image_path},
                {"type": "text", "text": text_prompt},
            ],
        }
    ]
    
    try:
        # 生成推理用的文本信息
        text = processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        # 处理视觉输入
        image_inputs, video_inputs = process_vision_info(messages)
        # 构建模型输入
        inputs = processor(
            text=[text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        )
        inputs = inputs.to(model.device)
        
        # 生成模型输出
        with torch.no_grad():
            generated_ids = model.generate(**inputs, max_new_tokens=128)
            # 去除输入部分的token
            generated_ids_trimmed = [
                out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
            ]
            output_text = processor.batch_decode(
                generated_ids_trimmed,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False
            )
        return output_text[0]
    
    except Exception as e:
        return f"处理过程中出现错误: {str(e)}"

# -------------------------------
# 定义 Gradio 前端界面
# -------------------------------
with gr.Blocks() as demo:
    gr.Markdown("# 翻译演示")
    gr.Markdown("点击下面按钮以处理最新截图并进行翻译。")
    
    # 按钮触发翻译推理
    translate_btn = gr.Button("进行翻译", variant="primary")
    # 输出区域显示翻译结果
    output_textbox = gr.Textbox(label="输出结果")
    
    # 绑定按钮点击事件到翻译函数
    translate_btn.click(fn=process_image_and_text, outputs=output_textbox)

# -------------------------------
# 定义 FastAPI 应用，暴露翻译 API 接口
# -------------------------------
api_app = FastAPI()

@api_app.post("/translate")
async def translate_endpoint():
    """
    HTTP POST 请求到 /translate 时，调用 process_image_and_text() 并返回翻译结果。
    """
    result = process_image_and_text()
    return {"translation": result}

# -------------------------------
# 启动函数：同时启动 Gradio 界面和 FastAPI 接口
# -------------------------------
def start_gradio():
    demo.launch(
        server_name="0.0.0.0",
        server_port=7861,
        width=640,
        height=720,
        inbrowser=True,
        share=False
    )

if __name__ == "__main__":
    # 以线程方式启动 Gradio 前端界面
    gradio_thread = threading.Thread(target=start_gradio, daemon=True)
    gradio_thread.start()
    
    # 启动 FastAPI 服务，监听端口8000
    uvicorn.run(api_app, host="0.0.0.0", port=8000)
