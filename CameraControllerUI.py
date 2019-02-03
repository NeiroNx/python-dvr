from tkinter import Tk, Label, Button, Canvas, Frame, messagebox
import tkinter
import threading
from dvrip import DVRIPCam
import time

import cv2
import PIL.Image
import PIL.ImageTk


class VideoSource():
    def __init__(self, video_source=0):
        """Video Source class that handles the Stream from a specified source"""
        # Open the video source
        self.vid = cv2.VideoCapture(video_source)
        if not self.vid.isOpened():
            raise ValueError("Unable to open video source", video_source)

         # Get video source width and height
        self.width = self.vid.get(cv2.CAP_PROP_FRAME_WIDTH)
        self.height = self.vid.get(cv2.CAP_PROP_FRAME_HEIGHT)

    def get_frame(self):
        if self.vid.isOpened():
            ret, frame = self.vid.read()
            if ret:
                # Return a boolean success flag and the current frame converted to BGR
                return (ret, cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            else:
                return (ret, None)
        else:
            return (ret, None)

    # Release the video source when the object is destroyed
    def __del__(self):
        if self.vid.isOpened():
            self.vid.release()


class CameraControllerUI:
    """Simple UI Example that can control an SDETER Camera
    """

    def __init__(self, master, ip, password):
        self.master = master
        master.title("SDeter Camera Control & Surveilance")
        
        source = "rtsp://admin:{0}@{1}:554/h264/ch1/main/av_stream".format(
            password, ip)
        self.video_h = 480
        self.video_w = 720

        self.cam = DVRIPCam(ip, "admin", password)
        Button(master, text="Connect", width=15,
               command=lambda: self.connect(source)).grid(column=0, row=0)
    
        self.control_Frame = Frame(master)
        self.control_Frame.grid(column=0, row=1)
        self.left = Button(self.control_Frame, text="Left", width=15,
                           command=lambda: self.move_camera("Left")).grid(column=0, row=1)
        self.right = Button(self.control_Frame, text="Right", width=15,
                            command=lambda: self.move_camera("Right")).grid(column=2, row=1)
        self.up = Button(self.control_Frame, text="Up", width=15,
                         command=lambda: self.move_camera("Up")).grid(column=1, row=0)
        self.down = Button(self.control_Frame, text="Down", width=15,
                           command=lambda: self.move_camera("Down")).grid(column=1, row=1)

        self.canvas = Canvas(master, width=self.video_w, height=self.video_h)
        self.canvas.grid(column=0, row=2)

    def connect(self, source):
        try:
            self.cam.login()
            self.vid = VideoSource(source)
            self.update()
        except Exception as e:
            messagebox.showwarning(
                "Warning", "Connection failed : {0}".format(str(e)))

    def move_camera(self, direction):
        """This function moves the camera in the specified direction. The commands that are needed to be sent to the Camera are like :
        Direction<Up/Down/Left/Right>.  This function adds the Direction prefix by default.

        Arguments:
            direction {str} -- Options: Up | Down | Left | Right
        """

        def execute(direction):
            """Built in function to be executed on a different thread

            Arguments:
                direction {str} -- passed from the outer function
            """

            command = "Direction"+direction
            print(self.cam.move_it(command))
            time.sleep(0.5)
            self.stop_camera()

        threading.Thread(target=lambda: execute(direction)).start()

    def stop_camera(self):
        """Stops the Camera motion.
        """

        print(self.cam.stop_it())

    def update(self):
        """Callback to update the video stream from the camera
        """
        delay = 5
        # Get a frame from the video source
        ret, frame = self.vid.get_frame()
        self.photo = PIL.ImageTk.PhotoImage(
            image=PIL.Image.fromarray(frame))
        self.canvas.create_image(0, 0, image=self.photo)
        self.master.after(delay, self.update)


if __name__ == "__main__":
    root = Tk()
    #TODO : Sorry, I was lazy. You will have to manually insert the IP address for your Camera here.
    my_gui = CameraControllerUI(root, "192.168.137.21", "")
    root.mainloop()
