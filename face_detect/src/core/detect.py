import cv2
import numpy as np
import mediapipe as mp
import sys
import copy


threshold = {
    "image": {
        "detect_conf": 0.7,  # 检测到人脸
        "brightness": 130,  # 光照是否合适
        "is_blur": 100,  # 图片模糊的阈值，美颜磨皮算法会导致这个数值偏小
        "complete": 0.9,  # 图片完成度
        "pitch": 30,
        "yaw": 30,
        "roll": 30,
    },
    "eye": {
        "sun_glass": 80,  # 是否带墨镜的阈值
        "EAR": 0.18,  # 是否闭眼的阈值
    },
    "mouth": {
        "blue_mask": 0.2,
        "green_mask": 0.15,
        "white_mask": 0.25,
        "close": 5,  # 上下嘴唇距离, 是否闭嘴
        "laugh": 20,  # 上下嘴唇距离, 是否大笑
        "ratio": 5.5,  # 嘴巴宽高比
    },
    "occlude": {
        "brightness": 40,
        "blur": 30
    }
}


def face_detection(image):
    """
    检测脸是否存在
    """
    data = {
        "face_probability": "",
        "multiple_face": False
    }
    mp_face_detection = mp.solutions.face_detection
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    with mp_face_detection.FaceDetection(
        model_selection=0, min_detection_confidence=threshold["image"]["detect_conf"]
    ) as face_detection:
        results = face_detection.process(image_rgb)
        if not results.detections:
            return data, None
        if len(results.detections) > 1:
            data["multiple_face"] = True
            return data, None
        detection = results.detections[0]
        data["face_probability"] = detection.score[0]

        bbox = detection.location_data.relative_bounding_box
        h, w, _ = image.shape
        x1, y1 = int(bbox.xmin * w), int(bbox.ymin * h)
        x2, y2 = int((bbox.xmin + bbox.width) * w), int((bbox.ymin + bbox.height) * h)
        face_area = image[y1:y2, x1:x2]

    return data, face_area


def get_brightness(image):
    """
    检测亮度
    """
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    v = hsv[:, :, 2]
    return v.mean()


def get_variance(image):
    """
    检测是否模糊
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    variance = cv2.Laplacian(gray, cv2.CV_64F).var()
    return variance


def detect_occlude(image):
    return get_brightness(image), get_variance(image)


def extract_region(image, landmarks, indices):
    """
    根据landmarks和indices提取区域
    """
    h, w, _ = image.shape
    points = np.array([(int(landmarks[i].x * w), int(landmarks[i].y * h)) for i in indices])
    x, y, w, h = cv2.boundingRect(points)
    eye_region = image[y:y+h, x:x+w]
    return eye_region


def get_eye_region_status(eye_region):
    gray_eye = cv2.cvtColor(eye_region, cv2.COLOR_BGR2GRAY)
    mean_intensity = np.mean(gray_eye)
    return mean_intensity


def euclidean_distance(p1, p2):
    return np.linalg.norm(np.array(p1) - np.array(p2))


def calculate_ear(eye_points):
    # eye_points 是 [(x1,y1), (x2,y2), ...]
    A = euclidean_distance(eye_points[1], eye_points[5])
    B = euclidean_distance(eye_points[2], eye_points[4])
    C = euclidean_distance(eye_points[0], eye_points[3])
    ear = (A + B) / (2.0 * C)
    return ear


def get_region_data(image):
    mp_face_mesh = mp.solutions.face_mesh
    h, w, _ = image.shape
    with mp_face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1, refine_landmarks=True) as face_mesh:
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(image_rgb)
        landmarks = results.multi_face_landmarks[0].landmark
        # 墨镜区域, 后续按照这个区域去裁剪并做灰度检测
        LEFT_GLASS_LANDMARKS = [33, 133, 160, 159, 158, 157, 173, 246]
        RIGHT_GLASS_LANDMARKS = [362, 263, 387, 386, 385, 384, 398, 466]
        left_eye = extract_region(image, landmarks, LEFT_GLASS_LANDMARKS)
        right_eye = extract_region(image, landmarks, RIGHT_GLASS_LANDMARKS)
        # 左右眼坐标，会根据坐标进行EAR(Eye Aspect Ratio)闭眼检测
        LEFT_EYE_LANDMARKS = [33, 160, 158, 133, 153, 144]
        RIGHT_EYE_LANDMARKS = [362, 385, 387, 263, 373, 380]
        left_eye_points = [(int(landmarks[i].x * w), int(landmarks[i].y * h)) for i in LEFT_EYE_LANDMARKS]
        right_eye_points = [(int(landmarks[i].x * w), int(landmarks[i].y * h)) for i in RIGHT_EYE_LANDMARKS]
        # 嘴部坐标
        p13 = np.array([landmarks[13].x * w, landmarks[13].y * h])
        p14 = np.array([landmarks[14].x * w, landmarks[14].y * h])
        p82 = np.array([landmarks[82].x * w, landmarks[82].y * h])
        p87 = np.array([landmarks[87].x * w, landmarks[87].y * h])
        center_gap = np.linalg.norm(p13 - p14)
        side_gap = np.linalg.norm(p82 - p87)

        left_mouth = np.array([landmarks[61].x * w, landmarks[61].y * h])
        right_mouth = np.array([landmarks[291].x * w, landmarks[291].y * h])

        mouth_points = {
            "mouth_width": np.linalg.norm(left_mouth - right_mouth),
            "mouth_height": (center_gap + side_gap) / 2
        }
        mouth_points["ratio"] = mouth_points["mouth_width"] / (mouth_points["mouth_height"] + 1e-6)
        # 嘴巴 下巴区域，用于口罩检测
        LOWER_FACE_INDICES = (list(range(78, 88)) + list(range(308, 318)) + [152, 200, 201, 202, 172])
        mask_region = extract_region(image, landmarks, LOWER_FACE_INDICES)

        # 遮挡检测
        NOSE_INDEXES = [1, 2, 98, 195, 5]        # 鼻子
        MOUTH_INDEXES = [61, 291, 78, 308]       # 嘴角
        LEFT_EYE_INDEXES = [33, 133]             # 左眼角
        RIGHT_EYE_INDEXES = [362, 263]           # 右眼角
        CHEEK_INDEXES = [234, 454]               # 左右脸颊

        data = {
            "landmarks": landmarks,

            "left_glass_region": left_eye,
            "right_sunglass_region": right_eye,
            "left_eye_points": left_eye_points,
            "right_eye_points": right_eye_points,
            "mouth_points": mouth_points,
            "mask_region": mask_region,

            "nose_region": extract_region(image, landmarks, NOSE_INDEXES),
            "mouth_region": extract_region(image, landmarks, MOUTH_INDEXES),
            "left_eye_region": extract_region(image, landmarks, LEFT_EYE_INDEXES),
            "right_eye_region": extract_region(image, landmarks, RIGHT_EYE_INDEXES),
            "cheek_region": extract_region(image, landmarks, CHEEK_INDEXES)
        }
        return data


def detect_sunglass(left_eye, right_eye):
    left_eye_dark = get_eye_region_status(left_eye)
    right_eye_dark = get_eye_region_status(right_eye)
    return left_eye_dark, right_eye_dark


def detect_expression(mouth_width, mouth_height, threshold):
    ratio = mouth_width / (mouth_height + 1e-6)  # 防止除0
    if mouth_height < threshold["mouth"]["close"]:
        status = "close"
    elif ratio > threshold["mouth"]["ratio"] and mouth_height < threshold["mouth"]["laugh"]:
        status = "smile"
    elif ratio > threshold["mouth"]["ratio"] and mouth_height >= threshold["mouth"]["laugh"]:
        status = "laugh"
    else:
        status = "unknown"
    return status


def detect_mask_region(image):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    # 蓝色口罩（如医用外科口罩）
    lower_blue = np.array([90, 50, 50])
    upper_blue = np.array([130, 255, 255])
    blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)
    blue_ratio = np.sum(blue_mask > 0) / (image.shape[0] * image.shape[1])

    # 绿色口罩（如某些布口罩）
    lower_green = np.array([45, 50, 50])
    upper_green = np.array([80, 255, 255])
    green_mask = cv2.inRange(hsv, lower_green, upper_green)
    green_ratio = np.sum(green_mask > 0) / (image.shape[0] * image.shape[1])

    # 白色口罩（浅色，高亮低饱和度区域）
    lower_white = np.array([0, 0, 180])
    upper_white = np.array([180, 50, 255])
    white_mask = cv2.inRange(hsv, lower_white, upper_white)
    white_ratio = np.sum(white_mask > 0) / (image.shape[0] * image.shape[1])
    return blue_ratio, green_ratio, white_ratio


def estimate_head_pose(image, landmarks):
    h, w = image.shape[:2]
    # 人脸关键点索引：用于姿态估计
    FACE_POINTS_ID = {
        "nose_tip": 1,
        "left_eye_outer": 33,
        "right_eye_outer": 263,
        "mouth_left": 61,
        "mouth_right": 291,
        "chin": 152
    }

    # 对应的3D模型坐标（单位可以任意，比例一致即可）
    model_points = np.array([
        [0.0, 0.0, 0.0],         # nose tip
        [-30.0, -30.0, -30.0],   # left eye outer
        [30.0, -30.0, -30.0],    # right eye outer
        [-30.0, 30.0, -30.0],    # mouth left
        [30.0, 30.0, -30.0],     # mouth right
        [0.0, 70.0, -50.0]       # chin
    ])

    image_points = []
    for key in FACE_POINTS_ID.values():
        landmark = landmarks[key]
        x = int(landmark.x * w)
        y = int(landmark.y * h)
        image_points.append((x, y))
    image_points = np.array(image_points, dtype="double")

    # 相机矩阵
    focal_length = w
    center = (w / 2, h / 2)
    camera_matrix = np.array([
        [focal_length, 0, center[0]],
        [0, focal_length, center[1]],
        [0, 0, 1]
    ], dtype="double")

    dist_coeffs = np.zeros((4, 1))  # 假设无畸变
    success, rotation_vector, translation_vector = cv2.solvePnP(
        model_points, image_points, camera_matrix, dist_coeffs, flags=cv2.SOLVEPNP_ITERATIVE
    )
    # 将 rotation_vector 转为欧拉角（pitch, yaw, roll）
    rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
    pose_mat = cv2.hconcat((rotation_matrix, translation_vector))
    _, _, _, _, _, _, eulerAngles = cv2.decomposeProjectionMatrix(pose_mat)

    pitch, yaw, roll = eulerAngles.flatten()
    return pitch, yaw, roll


def get_complete_rate(landmarks, margin=0.05):
    count_inside = 0
    for lm in landmarks:
        if margin < lm.x < 1 - margin and margin < lm.y < 1 - margin:
            count_inside += 1

    ratio = count_inside / len(landmarks)
    return ratio


def main(image_path):
    status = {
        "legal": False,
        "face_detect": None,
        "multiple_face": None,
        "is_bright": None,
        "is_blur": None,
        "has_sun_glass": None,
        "eye_close": None,
        "has_mask": None,
        "expression": None,
        "pose": None,
        "is_complete": None,
        "extra": {
            "nose_occlude": None,
            "mouth_occlude": None,
            "left_eye_occlude": None,
            "right_eye_occlude": None,
            "cheek_occlude": None
        }
    }
    confidence = copy.deepcopy(status)

    image = cv2.imread(image_path)
    data, face_area = face_detection(image)
    # 是否检测到人脸
    if not data["face_probability"]:
        status["face_detect"] = False
        return status, confidence

    # 人脸的阈值是否够
    if data["face_probability"] < threshold["image"]["detect_conf"]:
        status["face_detect"] = False
        confidence["face_detect"] = threshold["image"]["detect_conf"]
        return status, confidence
    else:
        status["face_detect"] = True
        confidence["face_detect"] = threshold["image"]["detect_conf"]

    # 是否会检测到多张人脸
    if data["multiple_face"]:
        status["multiple_face"] = True
        return status, confidence

    status["multiple_face"] = False
    # 亮度是否够
    brightness = get_brightness(image)
    confidence["is_bright"] = brightness
    if brightness < threshold["image"]["brightness"]:
        status["is_bright"] = False
        return status, confidence
    status["is_bright"] = True

    # 图片是否模糊, 磨皮美颜会导致这个过不了
    variance = get_variance(face_area)
    confidence["is_blur"] = variance
    if variance < threshold["image"]["is_blur"]:
        status["is_blur"] = True
        return status, confidence
    status["is_blur"] = False

    region_data = get_region_data(image)
    # print(region_data)

    # 人脸完整度
    complete_rate = get_complete_rate(region_data["landmarks"])
    confidence["is_complete"] = complete_rate
    if complete_rate < threshold["image"]["complete"]:
        status["is_complete"] = False
        return status, confidence
    status["is_complete"] = True

    # 是否戴墨镜，是否闭眼
    left_eye_dark, right_eye_dark = detect_sunglass(region_data["left_glass_region"], region_data["right_sunglass_region"])
    confidence["has_sun_glass"] = (left_eye_dark, right_eye_dark)
    if left_eye_dark < threshold["eye"]["sun_glass"] or right_eye_dark < threshold["eye"]["sun_glass"]:
        status["has_sun_glass"] = True
    status["has_sun_glass"] = False

    left_ear = calculate_ear(region_data["left_eye_points"])
    right_ear = calculate_ear(region_data["right_eye_points"])
    confidence["eye_close"] = (left_ear, right_ear)
    if left_ear < threshold["eye"]["EAR"] or right_ear < threshold["eye"]["EAR"]:
        status["eye_close"] = True
        return status, confidence
    status["eye_close"] = False

    # 是否戴口罩, 是否张嘴
    mask_region = region_data["mask_region"]
    blue_mask, green_mask, white_mask = detect_mask_region(mask_region)
    confidence["has_mask"] = (blue_mask, green_mask, white_mask)
    if (
        blue_mask > threshold["mouth"]["blue_mask"] or
        green_mask > threshold["mouth"]["green_mask"] or
        white_mask > threshold["mouth"]["white_mask"]
    ):
        status["has_mask"] = True
    else:
        status["has_mask"] = False

    expression = detect_expression(
        region_data["mouth_points"]["mouth_width"],
        region_data["mouth_points"]["mouth_height"],
        threshold
    )
    confidence["expression"] = (region_data["mouth_points"]["mouth_width"], region_data["mouth_points"]["mouth_height"])
    status["expression"] = expression
    if expression == "laugh":
        return status, confidence

    pitch, yaw, roll = estimate_head_pose(image, region_data["landmarks"])
    confidence["pose"] = (pitch, yaw, roll)
    if (
        abs(pitch) < threshold["image"]["pitch"] and
        abs(yaw) < threshold["image"]["yaw"] and
        abs(roll) < threshold["image"]["roll"]
    ):
        status["pose"] = True
    else:
        status["pose"] = False
        return status, confidence

    nose_occlude = detect_occlude(region_data["nose_region"])
    mouth_occlude = detect_occlude(region_data["mouth_region"])
    left_eye_occlude = detect_occlude(region_data["left_eye_region"])
    right_eye_occlude = detect_occlude(region_data["right_eye_region"])
    cheek_occlude = detect_occlude(region_data["cheek_region"])
    tmp = {
        "nose_occlude": nose_occlude,
        "mouth_occlude": mouth_occlude,
        "left_eye_occlude": left_eye_occlude,
        "right_eye_occlude": right_eye_occlude,
        "cheek_occlude": cheek_occlude
    }
    t_bright = threshold["occlude"]["brightness"]
    t_blur = threshold["occlude"]["blur"]
    for k, v in tmp.items():
        confidence["extra"][k] = v
        if v[0] < t_bright or v[1] < t_blur:
            status["extra"][k] = True
        else:
            status["extra"][k] = False
    status["legal"] = True
    return status, confidence


class FaceDetector:
    """人脸检测器类"""
    
    def __init__(self):
        self.threshold = threshold
    
    def detect_faces(self, image_path):
        """检测人脸的主要方法"""
        return main(image_path)
    
    def detect_from_image(self, image):
        """从图像对象检测人脸"""
        # 保存临时图像并检测
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            cv2.imwrite(tmp_file.name, image)
            result = main(tmp_file.name)
            os.unlink(tmp_file.name)
            return result


def detect_faces(image_path):
    """检测人脸的便捷函数"""
    return main(image_path)


if __name__ == "__main__":
    status, confidence = main(sys.argv[1])
    print(status)
    print(confidence)
