"""Gets a video from the internet and uploads it"""

import urllib.request

from tiktok_uploader.upload import upload_video

URL = "https://raw.githubusercontent.com/wkaisertexas/wkaisertexas.github.io/main/upload.mp4"
FILENAME = "upload.mp4"

if __name__ == "__main__":
    # download random video
    # urllib.request.urlretrieve(URL, FILENAME)

    # upload video to TikTok
    upload_video(
        FILENAME,
        description="This is a #cool video I just downloaded. #wow #cool check it out on @tiktok",
        # cookies="cookies.txt",
        # cookies_list=[
        #     {
        #         'name': 'sessionid_ss',
        #         'value': '95539eeec4168350dca09bc11c9e2577',
        #         "domain": ".tiktok.com",
        #         'path': '/',
        #     },
        #     {
        #         'name': 'sessionid',
        #         'value': '95539eeec4168350dca09bc11c9e2577',
        #         "domain": ".tiktok.com",
        #         'path': '/',
        #     },
        #     {
        #         'name': 'msToken',
        #         'value': 'X7f5Sp7SMfV6NGUQoFwwqDisP48MJS2rya77qey7KHLv_unm4AVFF2VSWj3mp0uO6Ed6WzmhgiQGLMoiXsIesuIW6UPEKLzEXpm4JRg_ovirmI-pkqS8UOoqUofl3EL3wBICycUdTko0K8mwJmu2CVY=',
        #         "domain": ".tiktok.com",
        #         'path': '/',
        #     },
        # ]
        username="valebtinbest@gmail.com",
        password="|yR2mZtbc;hjS/T",
    )