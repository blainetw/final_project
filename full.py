import re
import sys
import requests
import json
import math
from statedraw import Plot, Region, mercator, main_map
from PIL import Image, ImageDraw
from PIL.ImageColor import getrgb


##allschools = set()
def filter_degrees(text):
    degrees = []
    REGEX1 = '''<h3>Education</h3><div class="profile-subsection">([().<>\w\s,\d&/-]*?)</div></div>'''
    if len(re.findall(REGEX1, text)) == 0:
        degrees.append("None")
    else:
        text2 = re.findall(REGEX1, text)[0]
        for d in re.finditer("([BMP]h?.[ASD]c?.) ([\w\s]*\w).*?<br>", text2):
            degrees.append(Degree(d.group(1), d.group(2)))
            ##if d.group(2) not in allschools:
                ##allschools | {d.group(2)}
        if len(degrees) == 0:
            degrees.append("None")
    return degrees

def filter_urls(text, url=""):
    """
    returns a list of urls found in the string 'text' that are
    (1) not media files and (2) within the specified domain.
    Args:
        text (str): a string that represents the text of a webpage
        domain (str): a <sub-domain> + '.' + <top-level domain>
    """
    REGEX1 = '''.*?williams.edu/'''
    urlsub = re.findall(REGEX1, url)[0]

    def extension_is_valid(url):
        EXTS = ["jpg", "jpeg", "svg", "png", "pdf",
                "gif", "bmp", "mp3", "dvi"]
        for e in EXTS:
            if url.casefold().endswith(e):
                return False
        return True

    # '<a' + _not >_ + 'href=' + _quote_ + 'http://' + _nonquote_ + _quote_
    REGEX = '''profile/[\w\d]*?/'''
    urls = [(str(urlsub)+"{}".format(r)) for r in re.findall(REGEX, text)]
    return [url for url in urls if extension_is_valid(url)]


class Degree:

    def __init__(self, level, school):
        self._level = level
        self._school = school

    def school(self):
        return self._school

    def level(self):
        return self._level

class Institution:

    def __init__(self, name):
        self._name = name
        self._lat = ""
        self._lon = ""
        self._coords = ""
        self._degrees = {}
        self._total = sum([(int(count) for count in degree.values()) for degree in self._degrees.values()])

    def school_location(self):
        params = {"query": self._name, "key":"AIzaSyB2pPW9cRqj8up3fnDdWbjVZA_Em1UMZMY"}
        r = requests.get("https://maps.googleapis.com/maps/api/place/textsearch/json?parameters", params=params)
        self._lat = json.loads(r.text)["results"][0]["geometry"]["location"]["lat"]
        self._lon = json.loads(r.text)["results"][0]["geometry"]["location"]["lng"]
        self._coords = (self._lat, self._lon)

    def coords(self):
        return self._coords

    def lat(self):
        return self._lat

    def lon(self):
        return self._lon

    def degrees(self):
        return self._degrees

    def schoolname(self):
        return self._name

    #def point(self):

    def __repr__(self):
        return "degrees: {}, coordinates: {}".format(self._degrees, self.coordinates())

class AllInstitutions:

    def __init__(self):
        self._institutions = set()
        self._total = ""

    def percentages(self):
        self._total = sum([institution._total for institution in self._institutions])

    def insts(self):
        return self._institutions

    def total(self):
        return self._total


class Department:
    def __init__(self, url):
        self._url = url
        self._faculty = {}


class DeptWeb:

    def __init__(self, url):
        """
        Initializes a WebPage's state with the url, and populates:
        - the set of urls in the WebPages's source
        - the set of emails in the WebPages's source
        - the set of phone numbers in the WebPages's source
        Args:
            url (str): the url to search
        """
        self._url = url
        self._urls = set()
        self._profs = set()
        self._text = ""
        self._name = ""

    def __hash__(self):
        """Return the hash of the URL"""
        return hash(self.url())

    def __eq__(self, page):
        """
        return True if and only if the url of this page equals the url
        of page.
        Args:
            page (WebPage): a WebPage object to compare
        """
        return self._url == page._url

    def populate(self):
        """
        fetch this WebPage object's webpage text and populate its content
        """
        r = requests.get(self._url, auth =('user', 'pass'))
        if r.status_code == requests.codes.ok:
            self._text = r.text
            self._urls = self._urls | set(filter_urls(self._text, self._url))
            self._profs = self._profs | {Professor(url) for url in self._urls}
            self._name = re.findall('''<title>.*?(\w[\w\s]*?)</title>''', self._text)[0]

    def url(self):
        """return the url asssociated with the WebPage"""
        return self._url

    def profs(self):
        """return the phone numbers associated with the WebPage"""
        return self._profs

    def urls(self):
        """return the URLs associated with the WebPage"""
        return self._urls

    def name(self):
        return self._name

    def __repr__(self):
        """when website is printed, returns all professors"""
        return ("\n").join([str(p) for p in self._profs])

    """draw circle centered at coordinates weighted for relative number of graduates"""

class Professor:
    '''Professor class containing the url corresponding to their profile on the Williams website, a list containing their
    degrees (in the form of Degree objects), and their names. Contains methods that call other functions to populate
    the degree & name fields.'''
    def __init__(self, url):
        self._url = url
        self._ds = ""
        self._name = ""

    def assign_degrees(self):
        """assign degrees based on text from professor's webpage"""
        r = requests.get(self._url)
        self._ds = filter_degrees(r.text)

    def populate(self):
        r = requests.get(self._url)
        self._name = re.findall('''class="main-title">[\\r]?[\\n]?\s*?(\w[\w.,\s-]*?\w)\s*?</h1>''', r.text)[0]

    def name(self):
        return self._name

    def degrees(self):
        return self._ds

    def __repr__(self):
        return "{}: {}".format(self._name, self._ds)


class DetailPlot(Plot):
    def __init__(self, obj, mapfile):
        self._im = Image.open(mapfile)
        self.colors = {}
        self._schoolcoords = {}
        super().__init__(obj.width, obj.min_long, obj.min_lat, obj.max_long, obj.max_lat)

    def translate_coordinates(self, directory):
        for school in directory.keys():
            longitude = directory[school]["Object"].lon()
            latitude = directory[school]["Object"].lat()
            if (self.min_long <= longitude <= self.max_long) and (self.min_lat <= latitude <= self.max_lat):
                r = Region([(longitude, mercator(latitude))])
                self._schoolcoords[school] = (self.trans_long(r)[0],self.trans_lat(r)[0])
            else:
                self._schoolcoords[school] = "N/A"
                continue

    def school_pts(self):
        draw = ImageDraw.Draw(self._im)
        for school in self._schoolcoords:
            if self._schoolcoords[school] != "N/A":
                center = self._schoolcoords[school]
                draw.ellipse([((float(center[0])+5), (float(center[1])+5)), ((float(center[0])-5), (float(center[1]-5)))], fill=getrgb("BLACK"))
            else:
                continue



    def draw_connections(self, source, directory, point1=None):
        """draws lines between the schools for each degree given in source by using the coordinates
        for schools given in directory, starting from Williams College and working backwards"""
        d = source
        if len(d) > 0:
            if point1 == None:
                p1 = (42.71280, -73.20302140000001)
            else:
                p1 = point1
            print(d[len(d)-1])
            if self._schoolcoords[d[len(d)-1].school()] != "N/A":
                p2 = self._schoolcoords[d.pop().school()]
                drawing = ImageDraw.Draw(self.im)
                drawing.line([p1,p2], fill=getrgb("BLUE"), width=5)
                self.draw_connections(d, directory, p2)

    def points(self, directory):
        """draws a point for each school in directory, aka each school at which a degree was received"""
        draw = ImageDraw.Draw(self.im)
        for school in directory:
            center = directory[school]["Object"].coords()
            draw.ellipse([(center[0]+5, center[1]+5), (center[0]-5, center[1]-5)])

    def new_save(self, filename):
        """save the current image to 'filename'"""
        self._im.save(filename, "PNG")


def main_details(urls, output, p_object):
    """for each website given, creates a department object that is then populated, and adds the schools attended and degrees received for each professor
    generates a map of the united states, then, using the scales created from this map generation, plots each professor's
    progression through academia, ending at Williams College"""

    i = Institution("Williams College")
    i._lat = 42.7128038
    i._lon = -73.20302140000001

    webs = {u for u in urls.split(',')}
    departments = set()
    allschools = {"Williams College":{"Object":i}}
    institutions = {}
    all_degree_levels = set()
    for web in webs:
        dept = DeptWeb(web)
        dept.populate()
        departments = departments | {dept}
        for p in dept.profs():
            p.populate()
            p.assign_degrees()
            if p.degrees()[0] != "None":
                for d in p.degrees():
                    dtype_count = {}
                    if d.school() not in allschools:
                        dtype_count[d.level()] = 1
                        allschools[d.school()] = {"Degrees": {dept.name(): dtype_count}}
                    elif d.school() in allschools:
                        if dept.name() in allschools[d.school()]["Degrees"].keys() and d.level() in allschools[d.school()]["Degrees"][dept.name()].keys():
                            allschools[d.school()]["Degrees"][dept.name()][d.level()] += 1
                        else:
                            allschools[d.school()]["Degrees"][dept.name()][d.level()] = 1
                    all_degree_levels = all_degree_levels | {d.level()}
            else:
                continue
    return departments
    return allschools
    for school in allschools.keys():
        if Institution(school) not in allschools[school].values():
            i = Institution(school)
            i._degrees = allschools[school]
            i.school_location()
            allschools[school]["Object"] = i
        else:
            continue
    details = DetailPlot(p_object, "mapoutline.png")
    details.translate_coordinates(allschools)
    details.school_pts()
    for department in departments:
        for professor in department.profs():
            details.draw_connections(professor.degrees(), allschools)
    details.new_save(output)


            ###draw line between p1 and list.pop coordinate
            ##    use color corresponding to type of degree received @ p1
        #        weight according to number of other ppl who did the same
        #    point1 =
        #    f(d, p2)


if __name__ == '__main__':
    urls = sys.argv[1]
    output = sys.argv[2]
    boundaries = sys.argv[3]
    width = int(sys.argv[4])
    main_details(urls, output, main_map(boundaries, width))
