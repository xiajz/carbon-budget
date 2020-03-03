'''
c++ ../carbon-budget/emissions/cpp_util/calc_gross_emissions_generic.cpp -o ../carbon-budget/emissions/cpp_util//calc_gross_emissions_generic.exe -lgdal
'''

import argparse
import os
import datetime
import constants_and_names as cn
import universal_util as uu
from gain.mp_forest_age_category_natrl_forest import mp_forest_age_category_natrl_forest
from gain.mp_gain_year_count_natrl_forest import mp_gain_year_count_natrl_forest
from gain.mp_annual_gain_rate_natrl_forest import mp_annual_gain_rate_natrl_forest
from gain.mp_cumulative_gain_natrl_forest import mp_cumulative_gain_natrl_forest
from gain.mp_merge_cumulative_annual_gain_all_forest_types import mp_merge_cumulative_annual_gain_all_forest_types
from carbon_pools.mp_create_carbon_pools import mp_create_carbon_pools
from emissions.mp_calculate_gross_emissions import mp_calculate_gross_emissions
from analyses.mp_net_flux import mp_net_flux
from analyses.mp_aggregate_results_to_10_km import mp_aggregate_results_to_10_km

def main ():

    model_stages = ['all', 'forest_age_category_natrl_forest', 'gain_year_count_natrl_forest',
                    'annual_gain_rate_natrl_forest', 'cumulative_gain_natrl_forest', 'removals_merged',
                    'carbon_pools', 'gross_emissions',
                    'net_flux', 'aggregate']


    # The argument for what kind of model run is being done: standard conditions or a sensitivity analysis run
    parser = argparse.ArgumentParser(description='Create tiles of the number of years of carbon gain for mangrove forests')
    parser.add_argument('--model-type', '-t', required=True, help='{}'.format(cn.model_type_arg_help))
    parser.add_argument('--stages', '-s', required=True,
                        help='Stages of creating Brazil legal Amazon-specific gross cumulative removals. Options are {}'.format(model_stages))
    parser.add_argument('--run_through', '-r', required=True,
                        help='Options: true or false. true: run named stage and following stages. false: run only named stage.')
    parser.add_argument('--run_date', '-d', required=True,
                        help='Date of run. Must be format YYYYMMDD.')
    parser.add_argument('--tile_id_list', '-l', required=True,
                        help='List of tile ids to use in the model. Should be of form 00N_110E or all.')
    parser.add_argument('--carbon-pool-extent', '-ce', required=False,
                        help='Extent over which carbon pools should be calculated: loss or 2000')
    parser.add_argument('--pools-to-use', '-p', required=False,
                        help='Options are soil_only or biomass_soil. Former only considers emissions from soil. Latter considers emissions from biomass and soil.')
    parser.add_argument('--tcd-threshold', '-tcd', required=False,
                        help='Tree cover density threshold above which pixels will be included in the aggregation.')
    parser.add_argument('--std-net-flux-aggreg', '-sagg', required=False,
                        help='The s3 standard model net flux aggregated tif, for comparison with the sensitivity analysis map')
    args = parser.parse_args()
    sensit_type = args.model_type
    stage_input = args.stages
    run_through = args.run_through
    run_date = args.run_date
    carbon_pool_extent = args.carbon_pool_extent
    pools = args.pools_to_use
    tile_id_list = args.tile_id_list
    thresh = args.tcd_threshold
    if thresh is not None:
        thresh = int(thresh)
    std_net_flux = args.std_net_flux_aggreg


    # Checks whether the sensitivity analysis argument is valid
    uu.check_sensit_type(sensit_type)


    # Checks the validity of the model stage arguments. If either one is invalid, the script ends.
    if (stage_input not in model_stages):
        raise Exception('Invalid stage selection. Please provide a stage from {}.'.format(model_stages))
    else:
        pass
    if (run_through not in ['true', 'false']):
        raise Exception('Invalid run through option. Please enter true or false.')
    else:
        pass


    # Generates the list of stages to run
    actual_stages = uu.analysis_stages(model_stages, stage_input, run_through)
    print "Analysis stages to run:", actual_stages


    # Checks if the correct c++ script has been compiled for the pool option selected.
    # Does this up front so that the user is prompted to compile the C++ before the script starts running, if necessary.
    if 'gross_emissions' in actual_stages:

        if pools == 'biomass_soil':
            # Some sensitivity analyses have specific gross emissions scripts.
            # The rest of the sensitivity analyses and the standard model can all use the same, generic gross emissions script.
            if sensit_type in ['no_shifting_ag', 'convert_to_grassland']:
                if os.path.exists('../carbon-budget/emissions/cpp_util/calc_gross_emissions_{}.exe'.format(sensit_type)):
                    print "C++ for {} already compiled.".format(sensit_type)
                else:
                    raise Exception('Must compile standard {} model C++...'.format(sensit_type))
            else:
                if os.path.exists('../carbon-budget/emissions/cpp_util/calc_gross_emissions_generic.exe'):
                    print "C++ for generic emissions already compiled."
                else:
                    raise Exception('Must compile generic emissions C++...')

        elif (pools == 'soil_only') & (sensit_type == 'std'):
            if os.path.exists('../carbon-budget/emissions/cpp_util/calc_gross_emissions_soil_only.exe'):
                print "C++ for soil_only already compiled."
            else:
                raise Exception('Must compile soil_only C++...')

        else:
            raise Exception('Pool and/or sensitivity analysis option not valid')


    # If the tile_list argument is an s3 folder, the list of tiles in it is created
    if 's3://' in tile_id_list:
        tile_id_list = uu.tile_list_s3(tile_id_list, 'std')
        print tile_id_list
        print "There are {} tiles to process".format(str(len(tile_id_list))) + "\n"

    # Otherwise, check that the tile list argument is valid
    else:
        tile_id_list = uu.tile_id_list_check(tile_id_list)


    # List of output directories and output file name patterns
    raw_output_dir_list = [
                       cn.age_cat_natrl_forest_dir, cn.gain_year_count_natrl_forest_dir,
                       cn.annual_gain_AGB_natrl_forest_dir, cn.annual_gain_BGB_natrl_forest_dir,
                       cn.cumul_gain_AGCO2_natrl_forest_dir, cn.cumul_gain_BGCO2_natrl_forest_dir,
                       cn.annual_gain_AGB_BGB_all_types_dir, cn.cumul_gain_AGCO2_BGCO2_all_types_dir,
                       cn.AGC_emis_year_dir, cn.BGC_emis_year_dir, cn.deadwood_emis_year_2000_dir,
                       cn.litter_emis_year_2000_dir, cn.soil_C_emis_year_2000_dir, cn.total_C_emis_year_dir,
                       cn.net_flux_dir
                       ]

    raw_output_pattern_list = [
                           cn.pattern_age_cat_natrl_forest, cn.pattern_gain_year_count_natrl_forest,
                           cn.pattern_annual_gain_AGB_natrl_forest, cn.pattern_annual_gain_BGB_natrl_forest,
                           cn.pattern_cumul_gain_AGCO2_natrl_forest, cn.pattern_cumul_gain_BGCO2_natrl_forest,
                           cn.pattern_annual_gain_AGB_BGB_all_types, cn.pattern_cumul_gain_AGCO2_BGCO2_all_types,
                           cn.pattern_AGC_emis_year, cn.pattern_BGC_emis_year, cn.pattern_deadwood_emis_year_2000,
                           cn.pattern_litter_emis_year_2000, cn.pattern_soil_C_emis_year_2000, cn.pattern_total_C_emis_year,
                           cn.pattern_net_flux
                           ]


    # Creates age category tiles for natural forests
    if 'forest_age_category_natrl_forest' in actual_stages:

        print ':::::Creating forest age category for natural forest tiles'
        start = datetime.datetime.now()

        mp_forest_age_category_natrl_forest(sensit_type, tile_id_list, run_date = run_date)

        end = datetime.datetime.now()
        elapsed_time = end - start
        print ":::::Processing time for forest_age_category_natrl_forest:", elapsed_time, "\n"


    # Creates tiles of the number of years of removals for natural forests
    if 'gain_year_count_natrl_forest' in actual_stages:

        print ':::::Creating gain year count for natural forest tiles'
        start = datetime.datetime.now()

        mp_gain_year_count_natrl_forest(sensit_type, tile_id_list, run_date = run_date)

        end = datetime.datetime.now()
        elapsed_time = end - start
        print ":::::Processing time for gain_year_count_natrl_forest:", elapsed_time, "\n"


    # Creates tiles of annual AGB and BGB gain rate for non-mangrove, non-planted forest using the standard model
    # removal function
    if 'annual_gain_rate_natrl_forest' in actual_stages:

        print ':::::Creating annual removals for natural forest tiles'
        start = datetime.datetime.now()

        mp_annual_gain_rate_natrl_forest(sensit_type, tile_id_list, run_date = run_date)

        end = datetime.datetime.now()
        elapsed_time = end - start
        print ":::::Processing time for annual_gain_rate_natrl_forest:", elapsed_time, "\n"


    # Creates tiles of cumulative AGCO2 and BGCO2 gain rate for non-mangrove, non-planted forest using the standard model
    # removal function
    if 'cumulative_gain_natrl_forest' in actual_stages:

        print ':::::Creating cumulative removals for natural forest tiles'
        start = datetime.datetime.now()

        mp_cumulative_gain_natrl_forest(sensit_type, tile_id_list, run_date = run_date)

        end = datetime.datetime.now()
        elapsed_time = end - start
        print ":::::Processing time for cumulative_gain_natrl_forest:", elapsed_time, "\n"


    # Creates tiles of annual gain rate and cumulative removals for all forest types (above + belowground)
    if 'removals_merged' in actual_stages:

        print ':::::Creating annual and cumulative removals for all forest types combined (above + belowground) tiles'
        start = datetime.datetime.now()

        mp_merge_cumulative_annual_gain_all_forest_types(sensit_type, tile_id_list, run_date = run_date)

        end = datetime.datetime.now()
        elapsed_time = end - start
        print ":::::Processing time for removals_merged:", elapsed_time, "\n"


    # Creates carbon pools in loss year
    if 'carbon_pools' in actual_stages:

        print ':::::Creating emissions year carbon pools tiles'
        start = datetime.datetime.now()

        mp_create_carbon_pools(sensit_type, tile_id_list, carbon_pool_extent, run_date = run_date)

        end = datetime.datetime.now()
        elapsed_time = end - start
        print ":::::Processing time for carbon_pools:", elapsed_time, "\n"


    if 'gross_emissions' in actual_stages:

        print ':::::Creating gross emissions tiles'
        start = datetime.datetime.now()

        mp_calculate_gross_emissions(sensit_type, tile_id_list, pools, run_date = run_date)

        end = datetime.datetime.now()
        elapsed_time = end - start
        print ":::::Processing time for gross_emissions:", elapsed_time, "\n"


    if 'net_flux' in actual_stages:

        print ':::::Creating net flux tiles'
        start = datetime.datetime.now()

        mp_net_flux(sensit_type, tile_id_list, run_date = run_date)

        end = datetime.datetime.now()
        elapsed_time = end - start
        print ":::::Processing time for net_flux:", elapsed_time, "\n"


    if 'aggregate' in actual_stages:

        print ':::::Creating 10km aggregate maps'
        start = datetime.datetime.now()

        mp_aggregate_results_to_10_km(sensit_type, thresh, std_net_flux, run_date = run_date)

        end = datetime.datetime.now()
        elapsed_time = end - start
        print ":::::Processing time for aggregate:", elapsed_time, "\n"


if __name__ == '__main__':
    main()