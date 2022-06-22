# -*- coding: UTF-8 -*-

import csv
import logging
import os
import config as cfg
from urllib.request import urlopen
from datetime import datetime
from jinja2 import FileSystemLoader, Environment
from PIL import Image


# Basic logger configuration
logging.basicConfig(level=logging.DEBUG, format='<%(asctime)s %(levelname)s> %(message)s')
LOGGER = logging.getLogger(__name__)
TODAY = datetime.now()
LOGGER.info("=====> START %s <=====", TODAY)



# Read core config
PROJECTLIST_URL = cfg.csv_url
PROJECTLIST_TEMP_FILE = "project_list.csv"

def readCsvProjectList():
  if os.path.isfile(PROJECTLIST_TEMP_FILE):
    LOGGER.debug("Local project file exists: %s", PROJECTLIST_TEMP_FILE)
  else:
    gremiumUrl = PROJECTLIST_URL
    LOGGER.debug("Writing CSV from URL to temp file: %s", gremiumUrl)

    # Download from URL
    with urlopen(gremiumUrl) as file:
        content = file.read().decode()

    # Save to file
    with open(PROJECTLIST_TEMP_FILE, 'w') as download:
        download.write(content)


  LOGGER.debug("Reading Projects CSV file: %s", PROJECTLIST_TEMP_FILE)
  projects = []
  with open(PROJECTLIST_TEMP_FILE, newline="\n") as csvfile:
    next(csvfile, None) # skip first line of headlines (we have two headline rows)
    reader = csv.DictReader(csvfile)
    row_nr = 0
    for row in reader:
      row_nr = row_nr + 1
      if 1 == row_nr:
        LOGGER.info("Found columns: %s", row.keys())

      if ("Name" in row) and row["Name"]:
        if ("Filter" in row) and (row["Filter"] == "DF"):
          projects.append(row)
          LOGGER.info("Adding row %s: %s", row_nr, row["Name"])

          if ("Vorschaubild" in row) and row["Vorschaubild"]:
            image_file=row["Vorschaubild"]
            small_image_filename = '../images/small/' + image_file
            if os.path.exists(small_image_filename):
                LOGGER.debug("Skip image resize! File already exists: %s", image_file)
            else:
                resize_and_crop('../images/big/' + image_file, small_image_filename, [500,350])
                LOGGER.debug("Creating small image: %s", image_file)

        else:
          LOGGER.warning("Filter not 'DF' in row %s: %s", row_nr, row["Name"])
      else:
        LOGGER.warning("Empty row %s", row_nr)

  projects.sort(key=lambda x: x["Name"])

  return projects


def renderJinjaTemplate(directory, template_name, **kwargs):
    # Use Jinja2 Template engine for HTML generation
    # Source: https://daniel.feldroy.com/posts/jinja2-quick-load-function
    loader = FileSystemLoader(directory)
    env = Environment(loader=loader)
    template = env.get_template(template_name)
    return template.render(**kwargs)


def writeProjectDetails(projects):
    LOGGER.info("===========================> Writing project detail pages")
    htmlpath = '../html/'
    try:
        os.mkdir(htmlpath)
    except OSError as error:
        LOGGER.info(error)

    for project in projects:

        projectSlug = project["Vorschaubild"].split('.')[0]
        if not projectSlug:
            LOGGER.warning("No Vorschaubild! Skipping: %s", project["Name"])
            continue

        LOGGER.info("Project %s", projectSlug)
        projectFilename = projectSlug + '.html'
        templateData = {
            "DATE": datetime.today().strftime('%Y-%m-%d'),
            "PROJECT": project,
            "SLUG": projectSlug
        }
        html = renderJinjaTemplate("", "template-details-html.jinja2", **templateData)

        with open(htmlpath + projectFilename, 'w') as outfile:
            outfile.write(html)


def writeMarkdownFiles(projects):

    templateData = {
        "DATE": datetime.today().strftime('%Y-%m-%d'),
        "PROJECTS": projects
    }
    html = renderJinjaTemplate("", "template-projectlist.jinja2", **templateData)

    with open('../PROJECTS.md', 'w') as outfile:
        outfile.write(html)



def resize_and_crop(img_path, modified_path, size, crop_type='top'):
    """
    Resize and crop an image to fit the specified size.
    args:
        img_path: path for the image to resize.
        modified_path: path to store the modified image.
        size: `(width, height)` tuple.
        crop_type: can be 'top', 'middle' or 'bottom', depending on this
            value, the image will cropped getting the 'top/left', 'midle' or
            'bottom/rigth' of the image to fit the size.
    raises:
        Exception: if can not open the file in img_path of there is problems
            to save the image.
        ValueError: if an invalid `crop_type` is provided.
    """
    # If height is higher we resize vertically, if not we resize horizontally
    img = Image.open(img_path)
    # Get current and desired ratio for the images
    img_ratio = img.size[0] / float(img.size[1])
    ratio = size[0] / float(size[1])
    #The image is scaled/cropped vertically or horizontally depending on the ratio
    if ratio > img_ratio:
        img = img.resize((size[0], int(size[0] * img.size[1] / img.size[0])),
                Image.ANTIALIAS)
        # Crop in the top, middle or bottom
        if crop_type == 'top':
            box = (0, 0, img.size[0], size[1])
        elif crop_type == 'middle':
            box = (0, (img.size[1] - size[1]) / 2, img.size[0], (img.size[1] + size[1]) / 2)
        elif crop_type == 'bottom':
            box = (0, img.size[1] - size[1], img.size[0], img.size[1])
        else :
            raise ValueError('ERROR: invalid value for crop_type')
        img = img.crop(box)
    elif ratio < img_ratio:
        img = img.resize((int(size[1] * img.size[0] / img.size[1]), size[1]),
                Image.ANTIALIAS)
        # Crop in the top, middle or bottom
        if crop_type == 'top':
            box = (0, 0, size[0], img.size[1])
        elif crop_type == 'middle':
            box = ((img.size[0] - size[0]) / 2, 0, (img.size[0] + size[0]) / 2, img.size[1])
        elif crop_type == 'bottom':
            box = (img.size[0] - size[0], 0, img.size[0], img.size[1])
        else :
            raise ValueError('ERROR: invalid value for crop_type')
        img = img.crop(box)
    else :
        img = img.resize((size[0], size[1]),
                Image.ANTIALIAS)
        # If the scale is the same, we do not need to crop
    img.save(modified_path)


PROJECTS = readCsvProjectList()
writeMarkdownFiles(PROJECTS)
writeProjectDetails(PROJECTS)
