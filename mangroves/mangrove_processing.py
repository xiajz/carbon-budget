import utilities
import subprocess

def create_mangrove_tiles(tile_id):

    print "Getting bounding coordinates for tile", tile_id
    xmin, xmax, ymin, ymax = utilities.coords(tile_id)
    print "ymax:", ymax, "; ymin:", ymin, "; xmax", xmax, "; xmin:", xmin

    print ""
    out_tile = '{0}_{1}.tif'.format(utilities.mangrove_tile_out, tile_id)
    cmd = ['gdalwarp', '-t_srs', 'EPSG:4326', '-co', 'COMPRESS=LZW', '-tr', '0.00025', '0.00025', '-tap', '-te',
           xmin, ymin, xmax, ymax, '-dstnodata', '-9999', '-overwrite', utilities.mangrove_vrt, out_tile]
    subprocess.check_call(cmd)

    utilities.upload_final(utilities.mangrove_tile_out, utilities.out_dir, tile_id)


