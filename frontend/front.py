import gradio as gr
import subprocess
import os
from PIL import Image
import time
import pyautogui
import requests
import tkinter
import ctypes
from PIL import ImageGrab
from time import sleep
# ---------------------------
# 框选功能
# ---------------------------
class ScreenCapture:
    def __init__(self):
        self.__start_x, self.__start_y = 0, 0
        self.__end_x, self.__end_y = 0, 0
        self.__scale = 1

        # 创建窗口
        self.__win = tkinter.Tk()
        self.__win.attributes("-alpha", 0.5)  # 设置窗口半透明
        self.__win.attributes("-fullscreen", True)  # 设置全屏
        self.__win.attributes("-topmost", True)  # 设置窗口在最上层

        self.__width, self.__height = self.__win.winfo_screenwidth(), self.__win.winfo_screenheight()

        # 创建画布
        self.__canvas = tkinter.Canvas(self.__win, width=self.__width, height=self.__height, bg="gray")
        self.__canvas.pack()

        # 绑定事件
        self.__win.bind('<Button-1>', self.on_button_press)  # 绑定鼠标左键点击事件
        self.__win.bind('<ButtonRelease-1>', self.on_button_release)  # 绑定鼠标左键释放事件
        self.__win.bind('<B1-Motion>', self.on_mouse_move)  # 绑定鼠标左键点击移动事件
        self.__win.bind('<Escape>', lambda e: self.__win.destroy())  # 绑定Esc按键退出事件

        # 获取屏幕缩放比例
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32
        dc = user32.GetDC(None)
        widthScale = gdi32.GetDeviceCaps(dc, 8)  # 分辨率缩放后的宽度
        heightScale = gdi32.GetDeviceCaps(dc, 10)  # 分辨率缩放后的高度
        width = gdi32.GetDeviceCaps(dc, 118)  # 原始分辨率的宽度
        height = gdi32.GetDeviceCaps(dc, 117)  # 原始分辨率的高度
        self.__scale = width / widthScale

        self.__win.mainloop()  # 窗口持久化

    def on_button_press(self, event):
        """鼠标左键按下事件"""
        if event.state == 8:  # 鼠标左键按下
            self.__start_x, self.__start_y = event.x, event.y

    def on_button_release(self, event):
        """鼠标左键释放事件"""
        if event.state == 264:  # 鼠标左键释放
            if event.x == self.__start_x or event.y == self.__start_y:
                return

            self.__end_x, self.__end_y = event.x, event.y
            im = ImageGrab.grab((self.__scale * self.__start_x, self.__scale * self.__start_y,
                                 self.__scale * self.__end_x, self.__scale * self.__end_y))
            imgName = 'tmp.png'
            im.save(imgName)

            print(f"保存截图到 {imgName}")
            self.__win.update()
            sleep(0.5)
            self.__win.destroy()

    def on_mouse_move(self, event):
        """鼠标左键移动事件"""
        if event.x == self.__start_x or event.y == self.__start_y:
            return

        self.__canvas.delete("prscrn")
        self.__canvas.create_rectangle(self.__start_x, self.__start_y, event.x, event.y,
                                       fill='white', outline='red', tag="prscrn")

    def get_coordinates(self):
        """获取框选的坐标和大小"""
        width = abs(self.__end_x - self.__start_x)
        height = abs(self.__end_y - self.__start_y)
        return self.__start_x, self.__start_y, width, height


# Gradio 界面
def start_selecting_area():
    """启动框选区域功能"""
    selector = ScreenCapture()
    return selector.get_coordinates()

# ---------------------------
# 截屏与图片处理函数
# ---------------------------
def capture_and_resize(crop_area, custom_width, custom_height, custom_x, custom_y):
    """
    根据传入的 crop_area 参数截取屏幕后进行裁剪和缩放，返回处理后图片的保存路径。
    """
    timestamp = str(int(time.time()))
    temp_image_path = os.path.join("temppic", f"temp_screenshot_{timestamp}.png")
    
    # 截取整个屏幕并保存
    screenshot = pyautogui.screenshot()
    screenshot.save(temp_image_path)
    
    image = Image.open(temp_image_path)
    
    if crop_area == "下部":
        crop_width = 1600
        crop_height = 400
        cropped_image = image.crop((0, 790, crop_width, 790 + crop_height))
    elif crop_area == "中部":
        crop_width = 1600
        crop_height = 400
        cropped_image = image.crop((0, 490, crop_width, 490 + crop_height))
    elif crop_area == "上部":
        crop_width = 1600
        crop_height = 400
        cropped_image = image.crop((0, 190, crop_width, 190 + crop_height))
    elif crop_area == "全屏":
        crop_width = 1600
        crop_height = 1000
        cropped_image = image.crop((0, 190, crop_width, 190 + crop_height))
    elif crop_area == "定制":
        # 直接使用用户提供的参数
        if custom_width is None or custom_height is None or custom_x is None or custom_y is None:
            raise ValueError("定制区域必须输入有效的宽、高、X、Y数值！")
        crop_width = custom_width
        crop_height = custom_height
        x = custom_x
        y = custom_y
        cropped_image = image.crop((x, y, x + crop_width, y + crop_height))
    elif crop_area == "完整截屏":
        crop_width = 1600
        crop_height = 1000
        cropped_image = image.crop((0, 190, crop_width, 190 + crop_height))
    else:
        return None

    if crop_area == "完整截屏":
        save_image_path = os.path.join("savepic", f"full_screenshot_{timestamp}.png")
        cropped_image.save(save_image_path)
        return save_image_path
    else:
        # 缩放图片到宽度512像素，保持宽高比
        width = 512
        height = int(cropped_image.height * (width / cropped_image.width))
        resized_image = cropped_image.resize((width, height), Image.LANCZOS)
        resized_image.save(temp_image_path)
        return temp_image_path

# ---------------------------
# 调用翻译 API 的函数
# ---------------------------
def call_translation_api():
    """
    通过 HTTP POST 请求调用运行在 WSL 中的 FastAPI 翻译接口，获取翻译结果并返回纯文本。
    """
    api_url = "http://localhost:8000/translate"
    try:
        response = requests.post(api_url)
        if response.status_code == 200:
            result = response.json()
            translation = result.get("translation", "")
            return translation
        else:
            return f"请求失败，状态码：{response.status_code}"
    except Exception as e:
        return f"请求异常: {str(e)}"

# ---------------------------
# 合并截屏与翻译的生成器函数
# ---------------------------
def process_and_translate(crop_area, custom_width, custom_height, custom_x, custom_y):
    """
    根据指定的截屏区域进行截图处理，获取翻译结果并返回。
    """
    try:
        image_path = capture_and_resize(crop_area, custom_width, custom_height, custom_x, custom_y)
    except Exception as e:
        yield "", f"<div style='color:red;font-size:24px;font-weight:bold;'>错误: {str(e)}</div>"
        return

    yield image_path, ""
    
    if crop_area == "完整截屏":
        return
    
    raw_translation = call_translation_api()

    # 追加写入 history/history.txt（追加模式）
    if raw_translation:
        history_file = os.path.join("history", "history.txt")
        with open(history_file, "a", encoding="utf-8") as f:
            f.write(raw_translation + "\n")
    
    if raw_translation:
        formatted_translation = (
            f'<div style="border:2px solid #000; border-radius:8px; '
            f'padding:10px; background-color:#333; color:#fff; '
            f'box-shadow:2px 2px 8px rgba(0,0,0,0.3); '
            f'font-size:24px; font-weight:bold;">{raw_translation}</div>'
        )
    else:
        formatted_translation = ""
    
    yield image_path, formatted_translation

# ---------------------------
# Gradio 前端界面
# ---------------------------
with gr.Blocks(title="屏幕翻译工具", css=".gradio-button.primary {background-color: orange !important;}") as iface:
    gr.Markdown("## 视觉模型推理翻译器")

    # 输出区域：显示截屏图片和翻译结果
    image_output = gr.Image(label="截屏图片")
    translation_output = gr.HTML(label="翻译结果")

    # 隐藏的输入，用于传递截屏区域名称；默认设置为“定制”
    crop_area_input = gr.Textbox(value="定制", visible=False)
    
    # 新增4个参数输入框，用于“定制”区域，用户必须输入有效数值
    with gr.Row():
        custom_width_input = gr.Number(label="宽")
        custom_height_input = gr.Number(label="高")
        custom_x_input = gr.Number(label="X")
        custom_y_input = gr.Number(label="Y")
    
    with gr.Row():
        select_area_button = gr.Button("框选", variant="primary")
        btn_custom = gr.Button("定制", variant="primary")
        btn_full = gr.Button("全屏", variant="primary")
        btn_bottom = gr.Button("下部", variant="primary")
        btn_middle = gr.Button("中部", variant="primary")
        btn_top = gr.Button("上部", variant="primary")
        btn_full_screen = gr.Button("完整截屏", variant="primary")
    
    select_area_button.click(fn=start_selecting_area, outputs=[custom_x_input, custom_y_input, custom_width_input, custom_height_input])
    # 对于非“定制”的按钮，使用 JS 回调覆盖第一个输入（区域名称），其他参数保持输入框中的值不变
    btn_bottom.click(fn=process_and_translate,
                     inputs=[crop_area_input, custom_width_input, custom_height_input, custom_x_input, custom_y_input],
                     outputs=[image_output, translation_output],
                     js="() => ['下部', undefined, undefined, undefined, undefined]")
    btn_middle.click(fn=process_and_translate,
                     inputs=[crop_area_input, custom_width_input, custom_height_input, custom_x_input, custom_y_input],
                     outputs=[image_output, translation_output],
                     js="() => ['中部', undefined, undefined, undefined, undefined]")
    btn_top.click(fn=process_and_translate,
                  inputs=[crop_area_input, custom_width_input, custom_height_input, custom_x_input, custom_y_input],
                  outputs=[image_output, translation_output],
                  js="() => ['上部', undefined, undefined, undefined, undefined]")
    btn_full.click(fn=process_and_translate,
                   inputs=[crop_area_input, custom_width_input, custom_height_input, custom_x_input, custom_y_input],
                   outputs=[image_output, translation_output],
                   js="() => ['全屏', undefined, undefined, undefined, undefined]")
    btn_full_screen.click(fn=process_and_translate,
                          inputs=[crop_area_input, custom_width_input, custom_height_input, custom_x_input, custom_y_input],
                          outputs=[image_output, translation_output],
                          js="() => ['完整截屏', undefined, undefined, undefined, undefined]")
    # 对于“定制”按钮，不使用 JS 回调，保留隐藏输入默认值"定制"以及用户填写的4个参数
    btn_custom.click(fn=process_and_translate,
                     inputs=[crop_area_input, custom_width_input, custom_height_input, custom_x_input, custom_y_input],
                     outputs=[image_output, translation_output])
    
# ---------------------------
# 启动 Gradio 应用及窗口定位（仅适用于 Windows）
# ---------------------------
if __name__ == "__main__":
    if hasattr(iface, "queue"):
        iface = iface.queue()
    app, local_url, share_url = iface.launch(width=640, height=720, inbrowser=False)
    
    screen_width = pyautogui.size().width
    window_x = screen_width - 640
    window_y = 0
    window_handle = app.native_window_handle
    subprocess.run([
        "powershell", "-Command",
        f'$window = Get-Window -Id {window_handle}; $window.Move({window_x}, {window_y})'
    ])
