from flask import Flask, render_template, Response
from threading import Condition
import io
import logging

from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput

app = Flask(__name__)
picam2 = Picamera2()
picam2.configure(picam2.create_video_configuration(main={"size": (640, 480)}))


class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()


def gen_image():
    try:
        output = StreamingOutput()
        picam2.start_recording(JpegEncoder(), FileOutput(output))
        while True:
            with output.condition:
                output.condition.wait()
                frame = output.frame
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + bytes(frame) + b'\r\n')
    except Exception as ex:
        logging.warning('Exception is :  %s', str(ex))
    finally:
        picam2.stop_recording()


@app.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(gen_image(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/index')
def index():
    """Video streaming"""
    return render_template('index.html')


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000, threaded=True)
