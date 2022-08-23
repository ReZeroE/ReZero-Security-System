import cv2
import os
import time
from datetime import datetime

APPEND_VIDEO_THRESHOLD_TIME = 120 # how many seconds in between motion to create a new video (must be > 35 [vid takes 34 seconds to finish recording])
BUFFER_FRAME_COUNT = 50

NOISE_IGNORE_THRESHOLD = 1000 # default 1000

FRAMES_PER_VIDEO = 1000     # once motion is detected, record this many of frames as one batch
MOTION_THRESHOLD_ONE = 0.2  # threshold for motion-detected frames for the frames to be saved (one tenth of the number of total frames [FRAMES_PER_VIDEO/10])
MOTION_THRESHOLD_TWO = 0.3  # threshold for motion-detected frames for the frames to be saved (all frames [FRAMES_PER_VIDEO])

class MotionDetector:

    def __init__(self):
        self.vid_w = None
        self.vid_h = None
        self.vid_buffer_frames = []
        self.video_recorder = None

        self.motion_detected_time = 0
        self.motion_detected = False
        self.prev_vid_filename = None
        self.continue_vid = False # add new frames to the prev video file

    def detect_motion(self):
        video = cv2.VideoCapture(0)

        if self.vid_w == None and self.vid_h == None:
            self.vid_w  = video.get(3)
            self.vid_h = video.get(4)

        _, frame1 = video.read()
        _, frame2 = video.read()

        fps_frame_counter = 1
        prev_frame_time = 0
        curr_frame_time = 0
        curr_frame_time = time.time()
        fps = 'N/A'

        frame_list = []
        vid_frame_counter = 1

        while True:
            # detect motion =========================================================================================================================
            diff = cv2.absdiff(frame1, frame2)
            gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (5,5), 0)

            _, thresh = cv2.threshold(blur, 20, 255, cv2.THRESH_BINARY)
            dilated = cv2.dilate(thresh, None, iterations=3)
            contours, _ = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            
            if fps_frame_counter % 10 == 0:
                curr_frame_time = time.time()
                fps = str(int((10/(curr_frame_time-prev_frame_time))))
                prev_frame_time = curr_frame_time
            cv2.putText(frame1, fps, (7, 70), cv2.FONT_HERSHEY_SIMPLEX, 3, (100, 255, 0), 3, cv2.LINE_AA)
            fps_frame_counter += 1

            # motion detected =======================================================================================================================
            self.motion_detected = False
            for c in contours:
                (x, y, w, h) = cv2.boundingRect(c)
                if cv2.contourArea(c) < NOISE_IGNORE_THRESHOLD:
                    continue

                # check time between each video detection to determine whether a new video should be created
                self.motion_detected = True

                cv2.drawContours(frame1, contours, -1, (0, 255, 0), 1)
                cv2.rectangle(frame1, (x, y), (x+w, y+h), (255, 0, 0), 2)

            # check time between each video detection to determine whether a new video should be created ------------------------------------------------
            if self.motion_detected == True and vid_frame_counter == 1: # initial motion detected
                self.continue_vid = time.time() - self.motion_detected_time < APPEND_VIDEO_THRESHOLD_TIME

                if self.continue_vid:
                    print(f'next video is continuing in file {self.prev_vid_filename}')
                else:
                    print(f'next video is NOT continuing in file {self.prev_vid_filename}, time in between {time.time() - self.motion_detected_time}')

                self.motion_detected_time = time.time()

            # start counting frames for the recording when motion has been detected until vid frame counter hits 1000 frames ----------------------------
            if vid_frame_counter > 1 or self.motion_detected == True:
                vid_frame_counter += 1
                frame_list.append([frame1, self.motion_detected])
                print(f'motion detected, start recording: {vid_frame_counter}')


            # Check if the captured frames should be recorded ======================================================================================
            if vid_frame_counter % FRAMES_PER_VIDEO == 0 and vid_frame_counter is not 0:
                print('checking motion')
                record_frame_list = [] # frames to be recorded

                # check motion for first FRAMES_PER_VIDEO/10 frames -----------------------------------------------------------
                motion = 0
                one_tenth_frames = int(FRAMES_PER_VIDEO/10)
                for ct, fp in enumerate(frame_list):
                    if fp[1] == True: motion += 1
                    if ct == one_tenth_frames: break
                print(f'checking {one_tenth_frames} frames (motion: {motion})')
                if (motion / one_tenth_frames) > MOTION_THRESHOLD_ONE:
                    print(f'recording {one_tenth_frames} frames')
                    record_frame_list = frame_list.copy()[:one_tenth_frames]

                # check motion for all FRAMES_PER_VIDEO frames -------------------------------------------------------------
                motion = 0
                not_motion = 0
                for ct, fp in enumerate(frame_list):
                    if fp[1] == True: motion += 1
                    else: not_motion += 1

                print(f'checking {FRAMES_PER_VIDEO} frames (motion: {motion})')
                if (motion / FRAMES_PER_VIDEO) > MOTION_THRESHOLD_TWO:
                    print(f'recording {FRAMES_PER_VIDEO} frames')
                    record_frame_list = frame_list.copy()

                # record the frames into a video ----------------------------------------------------------------
                recorded = False
                if len(record_frame_list) > 0:
                    record_frame_list = [f[0] for f in record_frame_list]
                    self.record_video(record_frame_list)
                    recorded = True
                else:
                    print('Motion threshold not met for video to be recorded...')
                
                # reset all values ------------------------------------------------------------------------------
                vid_frame_counter = 1
                self.continue_vid = False
                if not recorded: 
                    self.motion_detected_time = 0
                frame_list.clear()


            # add buffer frames for the video recording =============================================================================================
            self.vid_buffer_frames.append(frame1)
            if len(self.vid_buffer_frames) > BUFFER_FRAME_COUNT:
                self.vid_buffer_frames.pop(0)

            # show video ============================================================================================================================
            cv2.imshow('feed', frame1)
            frame1 = frame2
            _, frame2 = video.read()
            key = cv2.waitKey(1)
            if key == ord('q'): break

        # end program
        video.release()
        cv2.destroyAllWindows()


    def record_video(self, frame_list):
        t = str(datetime.now().strftime("%m-%d-%Y-%H-%M-%S"))

        if not self.continue_vid:  # create new video file
            vid_name = os.path.abspath(os.path.dirname(__file__)) + f'/recordings/webcam-{t}.mp4'
            self.prev_vid_filename = vid_name
        else:                      # append to previous video file
            vid_name = self.prev_vid_filename

            cap = cv2.VideoCapture(vid_name)
            curr_vid_frame_list = []
            while(cap.isOpened()):
                ret, frame = cap.read()
                curr_vid_frame_list.append(frame)

                if not ret: break
            frame_list = curr_vid_frame_list + frame_list

        # create video writer object
        video = cv2.VideoWriter(vid_name, cv2.VideoWriter_fourcc(*'mp4v'), 25.0, (int(self.vid_w), int(self.vid_h)))

        # # # add buffer frames to the frame_list (if buffer frames are full)
        # if len(self.vid_buffer_frames) == BUFFER_FRAME_COUNT and len(frame_list) > BUFFER_FRAME_COUNT:
        #     vf_list = []
        #     for vf in self.vid_buffer_frames:
        #         vf_list.append(cv2.putText(vf, "Buffer Frames", (7, 70), cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 255, 0), 3, cv2.LINE_AA))
        #     frame_list = vf_list + frame_list

        # save frames to video
        for frame in frame_list:
            video.write(frame)

        video.release()


def run_program():
    while True:
        try:
            m = MotionDetector()
            m.detect_motion()
        except Exception as ex:
            print(ex)
            time.sleep(10)



if __name__ == '__main__':
    print('Delaying start for 30 seconds...')
    run_program()