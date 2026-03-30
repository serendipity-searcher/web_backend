# DMG S3 Bucket

# connecting and dumping the entire collection image data

## Connection

 # - bucket name: dmg-images-searcher
 # - region: eu-west-2
 # - access key & super secret key: SEE OLIVIER's EMAIL FROM 23.01.2025






# Observations

 # - all filenames are valid LINUX (/POSIX) filenames => can be downloaded to the same names
 # - there are 12251 folder, containing a sum 36652 files (avg of 3 files each)
 # - adding all file sizes together (and assuming they're in bytes), the bucket has a total size of 101GB
 # - estimate based on first few files, a download would take 5 hours


# Questions

 # - how persistent is the bucket? can I use it to store (computed) meta-info about its contents?
 #   (e.g. the computed mapping between file names and the object's IDs)
 #   -> could also help others/our future selves

 # - could you add the license data to the bucket? (as a simple CSV) for completeness' sake
 #   (i still have it somewhere but this way I can tidy up my data pipelines)

DATA_DIR = ".."

import sys

# setting path
sys.path.append(DATA_DIR)
print(sys.path)

import os

import pandas as pd
from pathvalidate import sanitize_filename
from tqdm import tqdm

from data import DMGImageHandler

tqdm.pandas()

import boto3

s3 = boto3.resource('s3')
bucket = s3.Bucket("dmg-images-searcher")


# def parse_filepath(s):
#     folder, file = s.rsplit("/", maxsplit=2)#[1:]
#     try:
#         obj_rendition, extension = file.rsplit(".", maxsplit=1)
#     except ValueError:
#         obj_rendition = file
#         extension = None

#     try:
#         obj_num, rendition_ind =  obj_rendition.rsplit("$", maxsplit=1)
#     except ValueError:
#         obj_num = obj_rendition
#         rendition_ind = None
#     # rendition_id = ((rendition_ind[0] if rendition_ind[0] else None) if rendition_ind else None)
#     return s, folder, obj_num, rendition_ind, extension


# def get_object_number(s):
#     return parse_filepath(s)[2]


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".tif", ".tiff", ".bmp", ".webp"}

def validate_filenames(filenames):
    files = [(f,)+os.path.split(f) for f in filenames]
    files = pd.DataFrame(files, columns=["raw", "prefix", "filename"])

    # filter out non-image files
    is_image = files.filename.apply(lambda f: os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS)
    skipped = files[~is_image]
    if len(skipped):
        print(f"Skipping {len(skipped)} non-image file(s): {skipped.filename.tolist()}")
    files = files[is_image].reset_index(drop=True)

    # files["object_number"] = files.raw.apply(get_object_number)
    obj_nums = DMGImageHandler.object_number_from_path("./" + files.raw)

    files["object_number"] = obj_nums

    clean = files.filename.apply(sanitize_filename)
    clean.name = "clean"
    files = pd.concat([files, clean], axis=1)
    assert len(files[~(files.filename == files.clean)]) == 0
    return files

def get_filesizes():
    sizes = [(obj.key, obj.size) for obj in tqdm(bucket.objects.all(), desc="enumerating file sizes...")]
    sizes = pd.Series([s[1] for s in sizes], index=[s[0] for s in sizes], name="filesize")
    sizes.index.name = "filename"
    return sizes

b2mb = lambda x: x/(1024**2)
b2gb = lambda x: b2mb(x)/1024
readable_size = lambda x: f"{b2mb(x):.2f} MB" if (b2mb(x) < 1000) else f"{b2gb(x):.2f} GB"


def download(save_path, row, redownload=False):
    prefix = save_path
    # prefix = "../data/test/"
    if not os.path.isdir(prefix+row.prefix):
        os.makedirs(prefix+row.prefix)
    if redownload or not os.path.exists(prefix+row.raw):
        bucket.download_file(row.raw, prefix+row.raw)
    elif (not redownload) and os.path.exists(prefix+row.raw):
        print(f"{prefix+row.raw} exists! skipping...")


from PIL import Image, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True

from colorthief import ColorThief

# def resize(save_path, row, new_path): #old_directory_name="images", new_directory_name="images_resized"):
#     def smaller(w, h):
#         fixed_size = 600 # CHANGED; WAS 1200
#         r = h/w
#         if w >= h:
#             return (fixed_size, int(fixed_size*r))
#         else:
#             r = 1/r
#             return (int(fixed_size*r), fixed_size)

#     with Image.open(save_path+row.raw) as img_handle:
#         new_size = smaller(*img_handle.size)
#         img_handle.thumbnail(new_size, Image.Resampling.LANCZOS)

#         # new_path = save_path.replace(old_directory_name, new_directory_name)

#         if not os.path.isdir(new_path+row.prefix):
#             os.makedirs(new_path+row.prefix)

#         img_handle.save(new_path+row.raw, quality=80) # CHANGED; WAS quality=90

#         return new_size


# def resize(image_handle, new_size, new_path):
#     def resize(w, h):
#         fixed_size = new_size # CHANGED; WAS 1200
#         r = h/w
#         if w >= h:
#             return (fixed_size, int(fixed_size*r))
#         else:
#             r = 1/r
#             return (int(fixed_size*r), fixed_size)
#     new_size = resize(*image_handle.size)
#     resized_image = image_handle.resize(new_size, Image.Resampling.LANCZOS)
#     if not os.path.isdir(new_path+row.prefix):
#         os.makedirs(new_path+row.prefix)
#     resized_image.save(new_path+row.raw, quality=80)
#     return new_size


def resize(image_handle, max_size):
    w, h = image_handle.size
    r = h/w
    if w >= h:
        new_size = (max_size, int(max_size*r))
    else:
        r = 1/r
        new_size = (int(max_size*r), max_size)
    return image_handle.resize(new_size, Image.Resampling.LANCZOS)


def save(row, path, image):
    if not os.path.isdir(path+row.prefix):
        os.makedirs(path+row.prefix)
    image.save(path+row.raw, quality=80)



def preprocess_image(save_path, row, thumb_path):
    color_thief = ColorThief(save_path+row.raw)
    try:
        dominant_colour = color_thief.get_color(quality=30)
    except Exception:
        dominant_colour = (0, 0, 0)
    dominant_colour = dict(zip(("dominant_R","dominant_G", "dominant_B"), dominant_colour))

    with Image.open(save_path+row.raw) as img_handle:
        orig_width, orig_height = img_handle.size

        if max(orig_width, orig_height) <= 1200:
            new_width, new_height = orig_width, orig_height
        else:
            resized_image = resize(img_handle, 1200)
            new_width, new_height = resized_image.size
            resized_image.save(save_path+row.raw, quality=80)

        thumb_full_path = thumb_path + row.raw
        if os.path.exists(thumb_full_path):
            with Image.open(thumb_full_path) as existing_thumb:
                thumb_width, thumb_height = existing_thumb.size
        else:
            thumb = resize(img_handle, 600)
            thumb_width, thumb_height = thumb.size
            save(row, thumb_path, thumb)

        paths = dict(object_number=row.object_number, filename=row.raw,
                     path=save_path+row.raw, thumb_path=thumb_path+row.raw)
        return dict(width=new_width, height=new_height,
                    thumb_width=thumb_width, thumb_height=thumb_height) | paths | dominant_colour



if __name__ == "__main__":
    auto_confirm = False
    limit = None
    save_folder = "images"
    save_path = f"./{save_folder}/"
    delete_original = False

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--save_path", help="path for saving downloaded images")
    parser.add_argument("--limit", help="only download {limit} many files", type=int)
    parser.add_argument("--confirmed", help="pre-confirm download", action="store_true")
    parser.add_argument("--delete_original", help="delete original images after download and downscaling", action="store_true")
    args = parser.parse_args()

    if args.save_path:
        save_path = args.save_path

    if args.limit:
        limit = args.limit

    if args.confirmed:
        auto_confirm = args.confirmed

    if args.delete_original:
        delete_original = True

    filenames_raw = [file.key for file in tqdm(bucket.objects.all(), desc="enumerating file names...")][:limit]
    filenames = validate_filenames(filenames_raw)

    sizes = get_filesizes()

    # filenames.to_csv(save_path + "filenames.csv", index=False)
    # sizes.to_csv(save_path + "sizes.csv")


    to_confirm = f"About to download {readable_size(sizes.sum())}, {len(filenames)} files... (y/n)?"

    if not (auto_confirm or input(to_confirm).lower().startswith("y")):
        exit()


    ### !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    k = 50
    #filenames = filenames.iloc[:k]

    print("\t(1 of 2) downloading images")
    def download_to_path(row, redownload=False):
        return download(save_path, row, redownload=redownload)
    filenames.apply(download_to_path, axis=1)




    print("\t(2 of 2) preprocessing images")
    thumbnails_path = os.path.join(os.path.dirname(save_path.rstrip("/")), "thumbnails") + "/"
    def preprocess_image_to_path(row):
        try:
            return preprocess_image(save_path, row, thumb_path=thumbnails_path)
        except Exception as e:
            print(f"Skipping {row.raw}: {e}")
            return None

    images_info = filenames.progress_apply(preprocess_image_to_path, axis=1)
    images_info = pd.DataFrame.from_records(images_info.dropna())
    images_info.to_csv(save_path+"image_info.csv", index=False)


    # resized_path = save_path.replace(save_folder, "images_resized")
    # def resize_to_path(row):
    #     return resize(save_path, row, new_path=resized_path)
    # thumb_sizes = filenames.progress_apply(resize_to_path, axis=1)


    import os
    if delete_original:
        # shutil.rmtree(save_path)
        os.rename(resized_path, save_path) # this overwrites the original download directory (by performing a mv)


