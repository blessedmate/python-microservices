import pika, json, tempfile, os
from bson.objectid import ObjectId
import moviepy.editor


def start(message, fs_videos, fs_mp3s, channel):
    message = json.loads(message)

    # Empty temp file
    tf = tempfile.NamedTemporaryFile()

    # Video contents
    out = fs_videos.get(ObjectId(message["video_file_id"]))

    # Add video contents to empty file
    tf.write(out.read())

    # Create audio from temp video file
    audio = moviepy.editor.VideoFileClip(tf.name).audio
    tf.close()

    # Write audio to a file
    tf_path = tempfile.gettempdir() + f"/{message['video_file_id']}.mp3"
    audio.write_audiofile(tf_path)

    # Save file to mongo
    f = open(tf_path, "rb")
    data = f.read()
    fid = fs_mp3s.put(data)
    f.close()
    os.remove(tf_path)

    message["mp3_file_id"] = str(fid)

    try:
        channel.basic_publish(
            exchange="",
            routing__key=os.environ.get("MP3_QUEUE"),
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE,
            ),
        )
    except Exception as err:
        fs_mp3s.delete(fid)
        return "Failed to publish message"
