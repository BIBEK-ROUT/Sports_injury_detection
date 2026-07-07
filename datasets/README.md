# 📊 Datasets — AI Sports Injury Risk Detection

This directory contains references, documentation, and links to all datasets used for training, testing, and evaluating the AI/ML models in this platform.

> ⚠️ **Note:** Raw dataset files are NOT stored in this repository due to size constraints. Use the links below to download them locally.

## 📁 Folder Structure (Planned)

```
datasets/
├── references/             # Dataset documentation and links
│   ├── human3.6m.md
│   ├── mpii_pose.md
│   ├── coco_keypoints.md
│   ├── sportspose.md
│   └── fifa_injury.md
├── preprocessing/          # Data preprocessing scripts
├── samples/                # Small sample files for testing
└── README.md
```

## 📦 Datasets Used

### 1. 🏃 Human3.6M Dataset
| Field | Info |
|-------|------|
| **Purpose** | Human pose estimation, joint tracking, movement analysis |
| **Size** | ~3.6 million video frames |
| **Format** | Video + 3D joint annotations |
| **Link** | [http://vision.imar.ro/human3.6m](http://vision.imar.ro/human3.6m) |

### 2. 🤸 MPII Human Pose Dataset
| Field | Info |
|-------|------|
| **Purpose** | Body keypoint detection, activity recognition |
| **Size** | ~25,000 images, 40,000+ annotated people |
| **Format** | Images + JSON keypoint annotations |
| **Link** | [http://human-pose.mpi-inf.mpg.de](http://human-pose.mpi-inf.mpg.de) |

### 3. 🏋️ COCO Keypoints Dataset
| Field | Info |
|-------|------|
| **Purpose** | Pose estimation training, human motion analysis |
| **Size** | ~200,000+ images |
| **Format** | Images + COCO JSON annotations |
| **Link** | [https://cocodataset.org/#keypoints-2020](https://cocodataset.org/#keypoints-2020) |

### 4. ⚽ SportsPose Dataset
| Field | Info |
|-------|------|
| **Purpose** | Sports-specific movement analysis, athlete posture assessment |
| **Format** | Video clips + pose annotations |
| **Link** | [https://github.com/ChristianIngwersen/SportsPose](https://github.com/ChristianIngwersen/SportsPose) |

### 5. 📋 FIFA Injury Dataset (Reference)
| Field | Info |
|-------|------|
| **Purpose** | Injury trend analysis, risk factor modeling |
| **Format** | Statistical injury reports |
| **Usage** | Reference only — for model validation and benchmarking |

## 🤖 How Datasets Are Used

| Module | Dataset Used |
|--------|-------------|
| Pose Estimation | Human3.6M, MPII, COCO Keypoints, SportsPose |
| Biomechanical Analysis | Human3.6M, SportsPose |
| Injury Risk Prediction | FIFA Injury Dataset (reference), SportsPose |
| Movement Anomaly Detection | Human3.6M, COCO Keypoints |
| Model Evaluation | MPII, COCO Keypoints |

## 📥 Download Instructions

```bash
# Example: Download COCO Keypoints
wget http://images.cocodataset.org/zips/train2017.zip
wget http://images.cocodataset.org/annotations/annotations_trainval2017.zip

# Extract
unzip train2017.zip -d datasets/coco/
unzip annotations_trainval2017.zip -d datasets/coco/
```

## 🔒 Data Privacy & Ethics

- All datasets used are **publicly available** research datasets
- No personal athlete data is stored in this repository
- Real athlete data uploaded via the platform is stored securely and is **never shared**
- All data handling complies with **GDPR** and sports data privacy guidelines
