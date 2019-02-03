import cv2
import numpy as np

#TODO replace PW and IP with your values
target = 'rtsp://admin:<PASSWORD>@<IP>:554/h264/ch1/main/av_stream'

cap = cv2.VideoCapture(target)

while(1):
    ret, frame = cap.read()

    cv2.imshow('frame', frame)
    k = cv2.waitKey(30) & 0xff
    if k == 27:
        break
cv2.destroyAllWindows()
cap.release()
