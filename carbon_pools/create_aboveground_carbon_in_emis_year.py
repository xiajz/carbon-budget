import datetime
import sys
import os
import numpy as np
import rasterio
sys.path.append('../')
import constants_and_names as cn
import universal_util as uu

def create_emitted_AGC(tile_id):

    # Only proceeds with running the function if there is a loss tile. Without a loss tile, there will be no output, so there's
    # no reason to call the function.
    if os.path.exists('{}.tif'.format(tile_id)):
        print "Loss tile found for {}. Processing...".format(tile_id)
    else:
        print "No loss tile for {}. Not processing.".format(tile_id)
        return

    # Start time
    start = datetime.datetime.now()

    # Names of the input tiles. Creates the names even if the files don't exist.
    mangrove_biomass_2000 = '{0}_{1}.tif'.format(tile_id, cn.pattern_mangrove_biomass_2000)
    natrl_forest_biomass_2000 = '{0}_{1}.tif'.format(tile_id, cn.pattern_WHRC_biomass_2000_unmasked)
    mangrove_cumul_AGC_gain = '{0}_{1}.tif'.format(tile_id, cn.pattern_cumul_gain_AGC_mangrove)
    planted_forest_cumul_AGC_gain = '{0}_{1}.tif'.format(tile_id, cn.pattern_cumul_gain_AGC_planted_forest_non_mangrove)
    natrl_forest_cumul_AGC_gain = '{0}_{1}.tif'.format(tile_id, cn.pattern_cumul_gain_AGC_natrl_forest)
    loss_year = '{0}.tif'.format(tile_id)

    # Name of output tile
    all_forests_AGC_emis_year = '{0}_{1}.tif'.format(tile_id, cn.pattern_AGC_emis_year)

    print "  Reading input files for {}...".format(tile_id)

    # Opens the input tiles if they exist. Any of these could not exist for a given Hansen tile.
    # Either mangrove biomass or WHRC biomass should exist for each tile, though. Thus, kwargs should ce
    # created based on one of those input tiles.
    try:
        mangrove_biomass_2000_src = rasterio.open(mangrove_biomass_2000)
        # Grabs metadata for one of the input tiles, like its location/projection/cellsize
        kwargs = mangrove_biomass_2000_src.meta
        # Grabs the windows of the tile (stripes) to iterate over the entire tif without running out of memory
        windows = mangrove_biomass_2000_src.block_windows(1)
        print "Mangrove biomass found for", tile_id
    except:
        print "No mangrove biomass for", tile_id

    try:
        natrl_forest_biomass_2000_src = rasterio.open(natrl_forest_biomass_2000)
        # Grabs metadata for one of the input tiles, like its location/projection/cellsize
        kwargs = natrl_forest_biomass_2000_src.meta
        # Grabs the windows of the tile (stripes) to iterate over the entire tif without running out of memory
        windows = natrl_forest_biomass_2000_src.block_windows(1)
        print "WHRC biomass found for", tile_id
    except:
        print "No WHRC biomass found for", tile_id

    try:
        mangrove_cumul_AGC_gain_src = rasterio.open(mangrove_cumul_AGC_gain)
        print "Mangrove carbon accumulation found for", tile_id
    except:
        print "No mangrove carbon accumulation for", tile_id

    try:
        planted_forest_cumul_AGC_gain_src = rasterio.open(planted_forest_cumul_AGC_gain)
    except:
        print "No planted forests for", tile_id

    try:
        natrl_forest_cumul_AGC_gain_src = rasterio.open(natrl_forest_cumul_AGC_gain)
    except:
        print "No non-mangrove non-planted forest carbon gain for", tile_id

    loss_year_src = rasterio.open(loss_year)

    # Updates kwargs for the output dataset.
    # Need to update data type to float 32 so that it can handle fractional gain rates
    kwargs.update(
        driver='GTiff',
        count=1,
        compress='lzw',
        nodata=0,
        dtype='float32'
    )

    # The output file: aboveground carbon density in the year of tree cover loss for pixels with tree cover loss
    dst_AGC_emis_year = rasterio.open(all_forests_AGC_emis_year, 'w', **kwargs)

    print "  Creating aboveground carbon in the year of loss for {}...".format(tile_id)

    # Iterates across the windows (1 pixel strips) of the input tiles
    for idx, window in windows:

        # Populates the output rasters' windows with 0s so that pixels without
        # any of the forest types will have 0s
        all_forest_types_C_combined = np.zeros((window.height, window.width), dtype='float32')

        # Creates a processing window for each forest type and calculates AGC density as biomass in 2000 + carbon accumulation

        # Does mangrove calculation if there is a mangrove biomass tile
        if os.path.exists(mangrove_biomass_2000):

            mangrove_biomass_2000_window = mangrove_biomass_2000_src.read(1, window=window)
            # print mangrove_biomass_2000_window[0][30020:30035]
            mangrove_cumul_AGC_gain_window = mangrove_cumul_AGC_gain_src.read(1, window=window)
            # print mangrove_cumul_AGC_gain_window[0][30020:30035]

            # Calculates the aboveground C density in mangrove pixels
            mangrove_C_final = (mangrove_biomass_2000_window * cn.biomass_to_c_mangrove) + mangrove_cumul_AGC_gain_window
            # print mangrove_C_final[0][30020:30035]

            all_forest_types_C_combined = all_forest_types_C_combined + mangrove_C_final
            # print all_forest_types_C_combined[0][30020:30035]

        # Does non-mangrove planted forest calculation if there is a planted forest C accumulation tile
        if os.path.exists(planted_forest_cumul_AGC_gain):

            natrl_forest_biomass_2000_window = natrl_forest_biomass_2000_src.read(1, window=window)
            # print natrl_forest_biomass_2000_window[0][30020:30035]
            planted_forest_cumul_AGC_gain_window = planted_forest_cumul_AGC_gain_src.read(1, window=window)
            # print planted_forest_cumul_AGC_gain_window[0][1270:1275]

            # Calculates the aboveground C density in non-mangrove planted forest pixels. The masking command makes sure that
            # only WHRC biomass pixels that correspond with non-mangrove planted forest pixels are included.
            # (Otherwise, all WHRC biomass pixels would be included in the planted forest calculation, not just the pixels
            # at planted forests.)
            planted_forest_C = (natrl_forest_biomass_2000_window * cn.biomass_to_c_natrl_forest) + planted_forest_cumul_AGC_gain_window
            # print planted_forest_C[0][1270:1275]
            planted_forest_C_final = np.ma.masked_where(planted_forest_cumul_AGC_gain_window == 0, planted_forest_C)
            planted_forest_C_final = planted_forest_C_final.filled(0)
            # print planted_forest_C_final[0][1270:1275]

            all_forest_types_C_combined = all_forest_types_C_combined + planted_forest_C_final
            # print all_forest_types_C_combined[0][30020:30035]

        # Does the non-mangrove non-planted forest calculation if there is a corresponding C accumulation tile
        if os.path.exists(natrl_forest_cumul_AGC_gain):

            natrl_forest_biomass_2000_window = natrl_forest_biomass_2000_src.read(1, window=window)
            # print natrl_forest_biomass_2000_window[0][30020:30035]
            natrl_forest_cumul_AGC_gain_window = natrl_forest_cumul_AGC_gain_src.read(1, window=window)
            # print natrl_forest_cumul_AGC_gain_window[0][1270:1275]

            # Calculates the aboveground C density in non-mangrove non-planted forest pixels. The masking commands make sure that
            # only WHRC biomass pixels that correspond with non-mangrove non-planted forest pixels are included.
            # (Otherwise, all WHRC biomass pixels would be included in the non-mang non-planted forest calculation, not just
            # the pixels in non-mang non-planted forests.)
            natural_forest_C = (natrl_forest_biomass_2000_window * cn.biomass_to_c_natrl_forest) + natrl_forest_cumul_AGC_gain_window
            # print natural_forest_C[0][1270:1275]
            natural_forest_C_final = np.ma.masked_where(planted_forest_cumul_AGC_gain_window > 0, natural_forest_C)
            natural_forest_C_final = np.ma.masked_where(mangrove_biomass_2000_window > 0, natural_forest_C_final)
            natural_forest_C_final = natural_forest_C_final.filled(0)
            # print natural_forest_C_final[0][30020:30035]

            all_forest_types_C_combined = all_forest_types_C_combined + natural_forest_C_final
            # print all_forest_types_C_combined[0][30020:30035]

        loss_year_window = loss_year_src.read(1, window=window)
        # print loss_year_window[[0]]

        # # Adds the carbon sums for all forest types together
        # all_forest_types_C_combined = mangrove_C_final + planted_forest_C_final + natural_forest_C_final
        # # print all_forest_types_C_combined[0][30020:30035]

        # Removes AGC pixels that do not have a loss year
        all_forest_types_C_final = np.ma.masked_where(loss_year_window == 0, all_forest_types_C_combined)
        all_forest_types_C_final = all_forest_types_C_final.filled(0)
        # print all_forest_types_C_final[0][30020:30035]

        # Converts the output to float32 since float64 is an unnecessary level of precision
        all_forest_types_C_final = all_forest_types_C_final.astype('float32')

        # Writes the output window to the output file
        dst_AGC_emis_year.write_band(1, all_forest_types_C_final, window=window)

        # sys.quit()

    # Prints information about the tile that was just processed
    uu.end_of_fx_summary(start, tile_id, cn.pattern_AGC_emis_year)