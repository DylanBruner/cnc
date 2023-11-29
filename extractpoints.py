import cv2

INPUT_IMAGE = "mountain.jpg"

def extract_points(path: str) -> list[tuple[int, int]]:
    points: list[tuple[int, int]] = []
    
    image = cv2.imread(path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5,5), 0)
    edged = cv2.Canny(gray, 35, 125)

    contours, hierarchy = cv2.findContours(edged, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

    for contour in contours:
        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)

        if len(approx) == 4:
            points = approx
            break

    # draw the outline of the shape
    cv2.drawContours(image, [points], -1, (0, 255, 0), 2)
    cv2.imwrite("output.jpg", image)