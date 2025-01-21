import json
import face_recognition

# Get personal info from json file
with open('config/config.json') as file:
  info = json.load(file)
  face_paths = info["face_paths"] # Locations for recognized faces' images
  face_encodings_path = info["face_encodings_path"] # Locations for recognized faces' encodings

print("Face paths loaded successfully")

# Load a sample picture of a face and learn how to recognize it.
known_face_encodings = []
for i in range(len(face_paths)):
    faceImg = face_recognition.load_image_file(face_paths[i])
    faceEncoding = face_recognition.face_encodings(faceImg)[0]
    known_face_encodings.append(faceEncoding)

print("Face encodings created successfully")

# Save the face encodings to a file
face_encodings_file = open(face_encodings_path, "w")
face_encodings_file.write(str(known_face_encodings))
face_encodings_file.close()

print("Face encodings saved successfully")