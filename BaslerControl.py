from pypylon import pylon
import tkinter.messagebox as messagebox


class CamControl:
    def __init__(self):
        self.camera = None
        self.converter = None

    def Connect(self):
        try:
            self.camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
            self.converter = pylon.ImageFormatConverter()
            self.converter.OutputPixelFormat = pylon.PixelType_BGR8packed
            self.converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned
            self.camera.Open()
            return 'OK'
        except Exception as e:
            print(e)
            error_msg = "Kiểm tra lại dây nguồn hoặc dây mạng kết nối của camera\n检查摄像机的电源线或网线\n "
            self.camera = None
            messagebox.showerror("Lỗi camera - Camera Error", error_msg)
            return str(e)

    def EnableChunks(self):
        try:
            nodemap = self.camera.GetNodeMap()
            chunk_mode_active = nodemap.GetNode("ChunkModeActive")
            if chunk_mode_active and pylon.IsWritable(chunk_mode_active):
                chunk_mode_active.SetValue(True)

            supported_chunks = ["Timestamp", "FrameCounter", "PayloadCRC16"]
            chunk_selector = nodemap.GetNode("ChunkSelector")
            chunk_enable = nodemap.GetNode("ChunkEnable")

            for chunk in supported_chunks:
                try:
                    if chunk_selector and chunk_enable:
                        chunk_selector.SetValue(chunk)
                        if pylon.IsWritable(chunk_enable):
                            chunk_enable.SetValue(True)
                        print(f"成功启用 Chunk 功能: {chunk}")
                except Exception as e:
                    print(f"无法启用 {chunk}: {e}")

        except Exception as e:
            print("启用 Chunk 功能時發生異常: ", e)

    def GrabImg(self):
        if not self.IsConnected():
            print("相机未连接，尝试重新连接...")
            if self.Connect() != 'OK':
                print("无法重新连接相机，抓取失败。")
                return None

        try:
            if not self.camera.IsGrabbing():
                self.camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

            result = self.camera.RetrieveResult(3000, pylon.TimeoutHandling_ThrowException)

            if result.GrabSucceeded():
                image = self.converter.Convert(result)
                img = image.GetArray()
                result.Release()
                return img
            else:
                print("CAM GrabImg error: ", result.ErrorCode)
                result.Release()
                return None

        except Exception as e:
            print("CAM GrabImg error: ", e)
            self.DisConnect()
            self.Connect()
            return None

    def DisConnect(self):
        if not self.IsConnected():
            print("Camera Disconnect")
            return 'OK'
        try:
            self.camera.Close()
            self.camera = None
            return 'OK'
        except Exception as e:
            print("CAM DisConnect 發生異常: ", e)
            return "Ngắt kết nối camera \nCAM DisConnect 發生異常: " + str(e)

    def IsConnected(self):
        return self.camera is not None and self.camera.IsOpen()


if __name__ == '__main__':
    cam = CamControl()
    status = cam.Connect()
    if status == 'OK':
        try:
            img = cam.GrabImg()
            if img is not None:
                print("GrabImg OK！")
            else:
                print("GrabImg Error！")
        finally:
            cam.DisConnect()
    else:
        print("Camera connect error！")

