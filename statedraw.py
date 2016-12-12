import sys
import csv
import math
from PIL import Image, ImageDraw
from PIL.ImageColor import getrgb


class Plot:

    """
    Provides the ability to map, draw and color regions in a long/lat
    bounding box onto a proportionally scaled image.
    """
    @staticmethod
    def interpolate(x_1, x_2, x_3, newlength):
        """
        linearly interpolates x_2 <= x_1 <= x_3 into newlength
        x_2 and x_3 define a line segment, and x_1 falls somewhere between them
        scale the width of the line segment to newlength, and return where
        x_1 falls on the scaled line.
        """
        return ((x_2 - x_1) / (x_2 - x_3)) * newlength

    @staticmethod
    def proportional_height(new_width, width, height):
        """
        return a height for new_width that is
        proportional to height with respect to width
        Yields:
            int: a new height
        """
        return (height / width) * new_width

    def __init__(self, width, min_long, min_lat, max_long, max_lat):
        """
        Create a width x height image where height is proportional to width
        with respect to the long/lat coordinates.
        """
        self.width = width
        self.min_long = min_long
        self.min_lat = min_lat
        self.max_long = max_long
        self.max_lat = max_lat
        self.im = Image.new("RGB", (int(self.width), int(self.proportional_height(self.width, (self.max_long - self.min_long), (self.max_lat - self.min_lat)))), (255,255,255))

    def save(self, filename):
        """save the current image to 'filename'"""
        self.im.save(filename, "PNG")

    def trans_lat(self, region):
        return [self.proportional_height(self.width, (self.max_long - self.min_long), (self.max_lat - self.min_lat)) - self.interpolate(x, self.min_lat, self.max_lat, self.proportional_height(self.width, (self.max_long - self.min_long), (self.max_lat - self.min_lat))) for x in region.lats()]

        """go from coords to image"""
    def trans_long(self, region):
        return [self.interpolate(x, self.min_long, self.max_long, self.width) for x in region.longs()]

    def draw_map(self, region):
        """
        Draws 'region' in the given 'style' at the correct position on the
        current image
        Args:
            region (Region): a Region object with a set of coordinates
            style (str): 'GRAD' or 'SOLID' to determine the polygon's fill
        """
        zl = list(zip(self.trans_long(region), self.trans_lat(region)))
        ImageDraw.Draw(self.im).polygon(zl, outline=getrgb("BLACK"))


class Region:
    """
    A region (represented by a list of long/lat coordinates) along with
    republican, democrat, and other vote counts.
    """

    def __init__(self, coords):
        self.coords = coords

    def longs(self):
        "Return a list of the longitudes of all the coordinates in the region"
        return [x for x, y in self.coords]

    def lats(self):
        "Return a list of the latitudes of all the coordinates in the region"
        return [y for x, y in self.coords]

    def min_lat(self):
        "Return the minimum latitude of the region"
        return min(self.lats())

    def min_long(self):
        "Return the minimum longitude of the region"
        return min(self.longs())

    def max_lat(self):
        "Return the maximum latitude of the region"
        return max(self.lats())

    def max_long(self):
        "Return the maximum longitude of the region"
        return max(self.longs())

def mercator(lat):
    """project latitude 'lat' according to Mercator"""
    lat_rad = (float(lat) * math.pi) / 180
    projection = math.log(math.tan((math.pi / 4) + (lat_rad / 2)))
    return (180 * projection) / math.pi


def main_map(boundaries, width):
    """
    Draws an image.
    This function creates an image object, constructs Region objects by reading
    in data from csv files, and draws polygons on the image based on those Regions

    Args:
        results (str): name of a csv file of election results
        boundaries (str): name of a csv file of geographic information
        output (str): name of a file to save the image
        width (int): width of the image
        style (str): either 'GRAD' or 'SOLID'
    """
    coords = []
    all_regions = []
    with open(boundaries, 'r') as fin:
        for line in list(csv.reader(fin)):
            coords.append([(float(line[x]),mercator(float(line[x+1]))) for x in range(2, (len(line)-1), 2)])
        for reg in coords:
            all_regions.append(Region(reg))
    lat_max = float(max([r.max_lat() for r in all_regions]))
    lat_min = float(min([r.min_lat() for r in all_regions]))
    long_max = float(max([r.max_long() for r in all_regions]))
    long_min = float(min([r.min_long() for r in all_regions]))
    p = Plot(width, long_min, lat_min, long_max, lat_max)
    for r in all_regions:
        p.draw_map(r)
    p.save("mapoutline.png")
    return p
