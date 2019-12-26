### This script combines the annual gain rate tiles from different forest types (non-mangrove natural forests, mangroves,
### plantations) into combined tiles. It does the same for cumulative CO2 gain over the study period (above and belowground).

import multiprocessing
import merge_cumulative_annual_gain_all_forest_types
import argparse
from functools import partial
import sys
sys.path.append('../')
import constants_and_names as cn
import universal_util as uu

def main ():

    # Files to download for this script. 'true'/'false' says whether the input directory and pattern should be
    # changed for a sensitivity analysis. This does not need to change based on what run is being done;
    # this assignment should be true for all sensitivity analyses and the standard model.
    download_dict = {
        cn.annual_gain_AGB_mangrove_dir: [cn.pattern_annual_gain_AGB_mangrove],
        cn.annual_gain_AGB_planted_forest_non_mangrove_dir: [cn.pattern_annual_gain_AGB_planted_forest_non_mangrove],
        cn.annual_gain_AGB_natrl_forest_dir: [cn.pattern_annual_gain_AGB_natrl_forest],

        cn.annual_gain_BGB_mangrove_dir: [cn.pattern_annual_gain_BGB_mangrove],
        cn.annual_gain_BGB_planted_forest_non_mangrove_dir: [cn.pattern_annual_gain_BGB_planted_forest_non_mangrove],
        cn.annual_gain_BGB_natrl_forest_dir: [cn.pattern_annual_gain_BGB_natrl_forest],

        cn.cumul_gain_AGCO2_mangrove_dir: [cn.pattern_cumul_gain_AGCO2_mangrove],
        cn.cumul_gain_AGCO2_planted_forest_non_mangrove_dir: [cn.pattern_cumul_gain_AGCO2_planted_forest_non_mangrove],
        cn.cumul_gain_AGCO2_natrl_forest_dir: [cn.pattern_cumul_gain_AGCO2_natrl_forest],

        cn.cumul_gain_BGCO2_mangrove_dir: [cn.pattern_cumul_gain_BGCO2_mangrove],
        cn.cumul_gain_BGCO2_planted_forest_non_mangrove_dir: [cn.pattern_cumul_gain_BGCO2_planted_forest_non_mangrove],
        cn.cumul_gain_BGCO2_natrl_forest_dir: [cn.pattern_cumul_gain_BGCO2_natrl_forest]
    }


    # List of output directories and output file name patterns
    output_dir_list = [cn.annual_gain_AGB_BGB_all_types_dir, cn.cumul_gain_AGCO2_BGCO2_all_types_dir]
    output_pattern_list = [cn.pattern_annual_gain_AGB_BGB_all_types, cn.pattern_cumul_gain_AGCO2_BGCO2_all_types]


    tile_id_list = uu.create_combined_tile_list(cn.WHRC_biomass_2000_non_mang_non_planted_dir,
                                             cn.annual_gain_AGB_mangrove_dir,
                                             set3=cn.annual_gain_AGB_planted_forest_non_mangrove_dir
                                             )
    # tile_id_list = ['00N_110E'] # test tiles
    print tile_id_list
    print "There are {} unique tiles to process".format(str(len(tile_id_list))) + '\n'


    # The argument for what kind of model run is being done: standard conditions or a sensitivity analysis run
    parser = argparse.ArgumentParser(description='Create tiles of the number of years of carbon gain for mangrove forests')
    parser.add_argument('--model-type', '-t', required=True,
                        help='{}'.format(cn.model_type_arg_help))
    args = parser.parse_args()
    sensit_type = args.model_type
    # Checks whether the sensitivity analysis argument is valid
    uu.check_sensit_type(sensit_type)


    # Downloads input files or entire directories, depending on how many tiles are in the tile_id_list
    for key, values in download_dict.iteritems():
        dir = key
        pattern = values[0]
        uu.s3_flexible_download(dir, pattern, '.', sensit_type, tile_id_list)


    # If the model run isn't the standard one, the output directory and file names are changed
    if sensit_type != 'std':

        print "Changing output directory and file name pattern based on sensitivity analysis"
        output_dir_list = uu.alter_dirs(sensit_type, output_dir_list)
        output_pattern_list = uu.alter_patterns(sensit_type, output_pattern_list)


    # For multiprocessing
    # Count/4 seems to pretty consistently use about 390 GB memory on an r4.16xlarge (not so much of an initial peak).
    # processes=18 maxes out at about 440 GB memory
    count = multiprocessing.cpu_count()
    pool = multiprocessing.Pool(processes=18)
    pool.map(partial(merge_cumulative_annual_gain_all_forest_types.gain_merge, output_pattern_list=output_pattern_list,
                     sensit_type=sensit_type), tile_id_list)

    # # For single processor use
    # for tile_id in tile_id_list:
    #     merge_cumulative_annual_gain_all_forest_types.gain_merge(tile_id, output_pattern_list, sensit_type)


    # Uploads output tiles to s3
    for i in range(0, len(output_dir_list)):
        uu.upload_final_set(output_dir_list[i], output_pattern_list[i])


if __name__ == '__main__':
    main()