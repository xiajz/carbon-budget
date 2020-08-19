from subprocess import Popen, PIPE, STDOUT, check_call
import datetime
import rasterio
import os
import sys
sys.path.append('../')
import constants_and_names as cn
import universal_util as uu

# Calls the c++ script to calculate gross emissions
def calc_emissions(tile_id, pools, sensit_type, folder):

    uu.print_log("Calculating gross emissions for", tile_id, "using", sensit_type, "model type...")

    start = datetime.datetime.now()

    # Runs the correct c++ script given the pools (biomass+soil or soil_only) and model type selected.
    # soil_only, no_shiftin_ag, and convert_to_grassland have special gross emissions C++ scripts.
    # The other sensitivity analyses and the standard model all use the same gross emissions C++ script.
    if (pools == 'soil_only') & (sensit_type == 'std'):
        cmd = ['{0}/calc_gross_emissions_soil_only.exe'.format(cn.docker_tmp), tile_id, sensit_type, folder]

    elif (pools == 'biomass_soil') & (sensit_type in ['convert_to_grassland', 'no_shifting_ag']):
        cmd = ['{0}/calc_gross_emissions_{1}.exe'.format(cn.docker_tmp, sensit_type), tile_id, sensit_type, folder]

    # This C++ script has an extra argument that names the input carbon pools and output emissions correctly
    elif (pools == 'biomass_soil') & (sensit_type not in ['no_shifting_ag', 'convert_to_grassland']):
        cmd = ['{0}/calc_gross_emissions_generic.exe'.format(cn.docker_tmp), tile_id, sensit_type, folder]

    else:
        uu.exception_log('Pool and/or sensitivity analysis option not valid')

    uu.log_subprocess_output_full(cmd)


    # Identifies which pattern to use for counting tile completion
    pattern = cn.pattern_gross_emis_commod_biomass_soil
    if (pools == 'biomass_soil') & (sensit_type == 'std'):
        pattern = pattern

    elif (pools == 'biomass_soil') & (sensit_type != 'std'):
        pattern = pattern + "_" + sensit_type

    elif pools == 'soil_only':
        pattern = pattern.replace('biomass_soil', 'soil_only')

    else:
        uu.exception_log('Pool option not valid')

    # Prints information about the tile that was just processed
    uu.end_of_fx_summary(start, tile_id, pattern)

# Adds metadata tags to the output rasters
def add_metadata_tags(tile_id, pattern, sensit_type):

    # tile = '{0}_{1}.tif'.format(tile_id, pattern)

    # # Opens the output tile, only so that metadata tags can be added
    # with rasterio.open(tile) as out_tile_src:
    #
    #     # Grabs metadata about the tif, like its location/projection/cellsize
    #     kwargs = out_tile_src.meta
    #
    #     out_tile_tagged = rasterio.open(tile, 'w', **kwargs)
    #
    #     # Adds metadata tags to the output raster
    #     uu.add_rasterio_tags(out_tile_tagged, sensit_type)
    #     out_tile_tagged.update_tags(
    #         units='megagrams CO2e/ha over model duration')
    #     out_tile_tagged.update_tags(
    #         extent='Tree cover loss within model extent. May also be for a specific tree cover loss driver (refer to file name).')

    out_tile = '{0}_{1}.tif'.format(tile_id, pattern)
    uu.print_log("Adding metadata tags to", out_tile)

    # with rasterio.open(out_tile, 'w+') as src:
    #
    #     src.update_tags(units='Mg CO2e over model duration (2001-20{})'.format(cn.loss_years),
    #                     source='Many data sources',
    #                     extent='Tree cover loss pixels')

    with rasterio.open(out_tile, 'r') as src:

        profile = src.profile

    with rasterio.open(out_tile, 'w', **profile) as dst:

        dst.update_tags(units='Mg CO2e over model duration (2001-20{})'.format(cn.loss_years),
                        source='Many data sources',
                        extent='Tree cover loss pixels')
        dst.close()
