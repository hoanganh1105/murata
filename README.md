# Murata


# Crawl Data 
Crawl videos (no sound), audios as well as description by powerful tools such as DrissionPage, yt-dlp.
<br><br>**Target**: By using Vector Semantics and Embedding, we aim to crawl data through keywords which are filtered to optimize productivity.







## Crawl data from Facebook Reels:
1.  **Introduction**
* For the outbreak of AI, there are so many videos on FB reels made by AI for educations in many fields. Nevertheless, there is no scientifically official confirmation for them. These are specific resources for our dataset.

* By using model Zipformer, we can extract audios in each video and convert into .txt files. You can accessing the model at the bottom of this page.


2.  **Step-by-step**
    * Authentication: Utilizes existing browser profiles (Cookies/Session Storage) to maintain login states.
    * Apply the mentioned model to extract audios and convert into text, (.mp4 is deleted after being extracted).
    * Path: `src\crawlers\facebook_reels\crawl_keyword.py`, and you can see our progress in `process_log.csv`.

3. **Zipformer-30M-RNNT-6000h** 
    * **Overview:** The Vietnamese Speech-to-Text (ASR) model is built on the ZipFormer architecture — an improved variant of the Conformer — featuring only 30 million parameters yet achieving exceptional performance in both speed and accuracy. On CPU, the model can transcribe a 12-second audio clip in just 0.3 seconds, significantly faster than most traditional ASR systems without requiring a GPU.
    * **Download Link:** [Zipformer-30M-RNNT-6000h](https://huggingface.co/hynt/Zipformer-30M-RNNT-6000h?fbclid=IwY2xjawQLz3hleHRuA2FlbQIxMABicmlkETJZeW54cHpXcUVnWDA3dXRic3J0YwZhcHBfaWQQMjIyMDM5MTc4ODIwMDg5MgABHiOSL2z_Exvbg0SxmFVa9BCM7ZNJZu733sYQ5mIGhayaKCxQ14q2XPfQcMfl_aem_jN6dFPVrRT7NvDghRk0RuQ)
   
