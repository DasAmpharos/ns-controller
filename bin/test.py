import cv2
import pytesseract

if __name__ == '__main__':
    frame = cv2.imread('frames/frame-0.jpg')
    frame = cv2.GaussianBlur(frame[81:128, 30:207], (5, 5), sigmaX=1, sigmaY=1)
    text = pytesseract.image_to_string(frame, lang='eng', config='--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789')
    print(text)

    while True:
        cv2.imshow('frame', frame)
        key = cv2.waitKey(0)
        if key == ord('q'):
            break
    cv2.destroyAllWindows()

    # for i in range(8):
    #     frame = cv2.imread(f'frames/berry-index-{i}.jpg')
    #     frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    #     frame = cv2.GaussianBlur(frame, (3, 3), sigmaX=0.5, sigmaY=0.5)
    #     frame = cv2.adaptiveThreshold(frame, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    #     while True:
    #         cv2.imshow('frame', frame)
    #         key = cv2.waitKey(0)
    #         if key == ord('q'):
    #             break
