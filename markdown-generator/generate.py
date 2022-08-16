# -*- coding: UTF-8 -*-

import logging
import json
import csv
import os
import config as cfg
from urllib.request import urlopen
from datetime import datetime
from jinja2 import FileSystemLoader, Environment
from PIL import Image


# Basic logger configuration
logging.basicConfig(level=logging.INFO, format='<%(asctime)s %(levelname)s> %(message)s')
LOGGER = logging.getLogger(__name__)
TODAY = datetime.now()
LOGGER.info("=====> START %s <=====", TODAY)



# Read core config
PROJECTLIST_URL = cfg.csv_url
PROJECTLIST_TEMP_FILE = "project_list.csv"

def readCsvProjectList():
  LOGGER.info("===========================> Assemble project list")

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
        row["SLUG"] = ""
        if ("Vorschaubild" in row and row["Vorschaubild"]):
            row["SLUG"] = row["Vorschaubild"].split('.')[0]

        if ("Filter" in row) and ((row["Filter"] == "DF") or (row["Filter"] == "DFMS")):
          projects.append(row)
          LOGGER.info("Adding row %s: %s (%s)", row_nr, row["Name"], row["Filter"])

          if ("Vorschaubild" in row) and row["Vorschaubild"]:
            image_file = row["Vorschaubild"]
            small_image_filename = '../images/small/' + image_file
            if os.path.exists(small_image_filename):
                LOGGER.debug("Skip image resize! File already exists: %s", image_file)
            else:
                resize_and_crop('../images/big/' + image_file, small_image_filename, [500,350])
                LOGGER.debug("Creating small image: %s", image_file)

        else:
          LOGGER.info("* Skipping row %s: %s (Filter not 'DF')", row_nr, row["Name"])
      else:
        LOGGER.warning("Empty row %s", row_nr)

  projects.sort(key=lambda x: x["Name"])

  return projects


def renderPersonInsideJinja(name):
    personString = name
    if name.startswith("https://github.com/"):
        unused_rest, username  = name.rsplit("github.com/")
        personString = '<a href="{}" target="_blank">@{}</a>'.format(name, username)
    elif name == "Github":
        personString = '<div class="image"><p><img style="height:auto" alt="Github.com" src="https://github.githubassets.com/images/modules/logos_page/GitHub-Logo.png" /></p></div>'

    return personString


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
    steckbriefpath = '../steckbriefe/'
    try:
        os.mkdir(htmlpath)
    except OSError as error:
        LOGGER.info(error)

    for project in projects:

        projectSlug = project["SLUG"]
        if not projectSlug:
            LOGGER.warning("No Slug! Skipping: %s", project["Name"])
            continue

        LOGGER.info("Project %s", projectSlug)
        projectFilename = projectSlug + '.html'
        templateData = {
            "DATE": datetime.today().strftime('%Y-%m-%d'),
            "PROJECT": project,
            "renderPersonInsideJinja": renderPersonInsideJinja
        }

        # write internal-vorlage-html
        html = renderJinjaTemplate("", "template-details-html.jinja2", **templateData)
        with open(htmlpath + projectFilename, 'w') as outfile:
            outfile.write(html)

        # write steckbrief html
        if project["Filter"] == "DFMS":
            html2 = renderJinjaTemplate("", "template-steckbrief.jinja2", **templateData)
            with open(steckbriefpath + projectFilename, 'w') as outfile:
                outfile.write(html2)


def writeSteckbriefIndex(projects):
    with open('../steckbriefe/index.html', 'w') as outfile:
        outfile.write(renderJinjaTemplate("", "template-steckbrief-index.jinja2",
            DATE= datetime.today().strftime('%Y-%m-%d'), PROJECTS=projects))


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


def writeJsonProjectListForSearchIframe(projects):
    LOGGER.info("===========================> Writing digifarm.json for search-iframe")

    fieldmapping = {"Aufgen. am": "Aufnahmedatum"}

    required_fields = [
        "Name", "Kurzbeschreibung", "Langbeschreibung", "Ursprung", "Quelle",
        "Kategorie", "Typ", "Komplexität", "Aufnahmedatum", "Projekt-Url",
        "Status", "Digifarm-Projekt", "Technik",
        "Inhalt", "Sponsor", "Technologien", "Kollaborationsplattform",
        "Quellcode", "Lizenz", "Projektstart", "Digifarm-Url", "Vorschaubild"
    ]
    json_projectlist = []

    for project in projects:

        for map_from, map_to in fieldmapping.items():
            project[map_to] = project[map_from]

        # only add münster projects to the iframe json list
        if (project["Filter"] == "DFMS"):

            # skip projects without image
            if not project["Vorschaubild"]:
                LOGGER.warning("No Vorschaubild! Skipping: %s", project["Name"])
                continue

            # convert preview image to valid uri
            project["Vorschaubild"] = "https://od-ms.github.io/digifarm-ms/images/small/" + project["Vorschaubild"]

            # make sure all keys we need are there
            for field in required_fields:
                if not field in project:
                    LOGGER.error("%s: missing required key '%s'", project["Name"], field)
                    continue

            # make sure ideenfarm url is set
            if not project["Digifarm-Url"]:
                LOGGER.error("%s: missing value for 'Digifarm-Url'", project["Name"])
                continue

            # remove unwanted keys & values from project dictionary
            reduced_project = {key: project[key] for key in required_fields}

            LOGGER.info("Adding %s", project["Name"])

            json_projectlist.append(reduced_project)

    jsonString = json.dumps(json_projectlist, indent=2)
    jsonFile = open("../../digifarm-search/data/digifarm.json", "w")
    jsonFile.write(jsonString)
    jsonFile.close()



PROJECTS = readCsvProjectList()
writeMarkdownFiles(PROJECTS)
writeSteckbriefIndex(PROJECTS)
writeProjectDetails(PROJECTS)
writeJsonProjectListForSearchIframe(PROJECTS)

