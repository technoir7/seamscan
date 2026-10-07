import subprocess


def transcode(src_path, dst_path, bitrate="128k"):
    proc = subprocess.Popen(
        "ffmpeg -y -i {} -b:a {} {}".format(src_path, bitrate, dst_path),
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return proc.communicate()
