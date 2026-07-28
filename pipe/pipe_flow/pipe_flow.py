import sys
import os 

import pandas as pd 

from pipe.pipe_flow.pipe_base import PipelineBase
from pipe.functions.functions_I import setup_dir, create_folder, source_import_api, source_edit, csv_import, sink_edit, forest_calculation
from pipe.functions.functions_II import country_name_to_alpha3


import warnings
warnings.filterwarnings('ignore')

sys.path.append(os.path.join(os.getcwd()))

#/////////////////////////////////////
#              PIPELINE
#/////////////////////////////////////

class PipelineFlow(PipelineBase):

    # Pipeline initialization
    def __init__(self) -> None:
        super().__init__()

    # RUN

    def run(self):

        s = self.config

        # START

        # Step . Base output folders set-up
        self.call_setup_output_dir(
            paths = [
                str(f"{s.out_csv_path}"),
                str(f"{s.out_fig_path}")
            ]
        )

        # Step . Create case-specific output folders
        self.call_create_case_output_folder(
            country = s.country, 
            region = s.region,
            site = s.site,
            paths = [
                str(f"{s.out_csv_path}"),
                str(f"{s.out_fig_path}")
            ]
        )

        # Step . Source load
        self.call_source_load(
            api_url= s.source_api_url,
            api_params = {
                'limit' : s.limit,
                'countries' : country_name_to_alpha3(s.country),
                'year': s.year,
                'subsectors': s.sector,
                # ADD SINGLE SITE?
            },
            out_path_country = str(f"{s.out_csv_path}{s.country}/{s.source_raw}"),
            out_path_region = str(f"{s.out_csv_path}{s.region}/{s.source_raw}"),
            out_path_site = str(f"{s.out_csv_path}{s.site}/{s.source_raw}"),
        )

        # Step . Sink load
        self.call_sink_load(
            country = s.country,
            region = s.region,
            site = s.site,
            threshold = s.threshold,
            forest_in_path = str(f"{s.in_csv_path}{s.forest_full}"),
            out_path_country = str(f"{s.out_csv_path}{s.country}/{s.sink_raw}"),
            out_path_region = str(f"{s.out_csv_path}{s.region}/{s.sink_raw}"),
            out_path_site = str(f"{s.out_csv_path}{s.site}/{s.sink_raw}"),
            source_site_path=str(f"{s.out_csv_path}{s.site}/{s.source_raw}")
        )

        # Step . Forest calculation
        self.call_forest_calculation(
            source_in_path_country=str(f"{s.out_csv_path}{s.country}/{s.source_raw}"),
            source_in_path_region=str(f"{s.out_csv_path}{s.region}/{s.source_raw}"),
            source_in_path_site=str(f"{s.out_csv_path}{s.site}/{s.source_raw}"),
            sink_in_path_country=str(f"{s.out_csv_path}{s.country}/{s.sink_raw}"),
            sink_in_path_region=str(f"{s.out_csv_path}{s.region}/{s.sink_raw}"),
            sink_in_path_site=str(f"{s.out_csv_path}{s.site}/{s.sink_raw}"),
            out_path_country=str(f"{s.out_csv_path}{s.country}/{s.forest_result}"),
            out_path_region=str(f"{s.out_csv_path}{s.region}/{s.forest_result}"),
            out_path_site=str(f"{s.out_csv_path}{s.site}/{s.forest_result}")
        )











#/////////////////////////////////////
#           CALL FUNCTIONS
#/////////////////////////////////////

    # Step . Output folders set-up
    def call_setup_output_dir(self, paths):

        s = self.config

        # Compile
        for path in paths:
            folder = setup_dir(str(path))

        # Success
        print(f"\n------------------- Base folders -------------------\n")
        return folder


    # Step . Output folders - case specific
    def call_create_case_output_folder(self, country, region, site, paths):

        s = self.config

        # Compile
        list_folders = []

        for path in paths:
            # Country level
            if country != 'None':
                folder = create_folder(str((f"{path}{country}")))
            else:
                pass
            # Region level 
            if region != 'None':
                folder = create_folder(str(f"{path}{region}"))
            else:
                pass
            # Site level
            if site != 'None':
                folder = create_folder(str(f"{path}{site}"))

        # Success
        print(f"\n------------------- Case folders -------------------\n")
        return paths, list_folders


    # Step . Source load
    def call_source_load(self, api_url, api_params, out_path_country, out_path_region, out_path_site):

        s = self.config

        # Import 
        source_in = source_import_api(api_url, api_params)
        
        # Compile
        source_out_country, source_out_region, source_out_site = source_edit(source_in,
                                                                             s.source_id_col,
                                                                             s.source_emit_col,
                                                                             s.source_lat_col,
                                                                             s.source_lon_col,
                                                                             s.source_name_col,
                                                                             s.url_region_api,
                                                                             s.language_region_api,
                                                                             s.country,
                                                                             s.region,
                                                                             s.site,
                                                                             s.source_country_col,
                                                                             s.source_region_col)

        # Export
        if s.country != 'None':
            source_out_country.to_csv(out_path_country, index=False)

        if s.region != 'None':
            source_out_region.to_csv(out_path_region, index=False)
        
        if s.site != 'None':
            source_out_site.to_csv(out_path_site, index=False)

        # Success
        print(f"\n------------------- Source data loaded -------------------\n")
        return source_out_country, source_out_region, source_out_site
    
    
    # Step . Sink load
    def call_sink_load(self, country, region, site, threshold, forest_in_path, out_path_country, out_path_region, out_path_site, source_site_path):

        s = self.config

        # Import 
        sink_in = csv_import(forest_in_path)
        if site != "None":
            source_site = csv_import(source_site_path)[s.source_region_col][0]
        else:
            source_site = pd.DataFrame()

        # Compile
        sink_out_country, sink_out_region, sink_out_site = sink_edit(
            sink_in,
            country,
            region,
            site,
            threshold,
            s.sink_country_col,
            s.sink_region_col,
            s.sink_site_col,
            s.sink_cover_col,
            s.sink_intake_col,
            s.sink_region_efficiency_col,
            s.sink_threshold_col,
            source_site,
            s.sink_country_efficiency_col
            )

        # Export
        if s.country != 'None':
            sink_out_country.to_csv(out_path_country, index = False)

        if s.region != 'None':
            sink_out_region.to_csv(out_path_region, index = False)
        
        if s.site != 'None':
            sink_out_site.to_csv(out_path_site, index = False)

        # Success
        print(f"\n------------------- Sink data loaded -------------------\n")
        return sink_out_country, sink_out_region, sink_out_site


    # Step . Forest calculation
    def call_forest_calculation(self, source_in_path_country, source_in_path_region, source_in_path_site, sink_in_path_country, sink_in_path_region, sink_in_path_site, out_path_country, out_path_region, out_path_site):
        
        s = self.config

        # Import 
        if s.country != 'None':
            source_country = csv_import(source_in_path_country)
            sink_country = csv_import(sink_in_path_country)
        else:
            source_country = pd.DataFrame()
            sink_country = pd.DataFrame()
        
        if s.region != 'None':
            source_region = csv_import(source_in_path_region)
            sink_region = csv_import(sink_in_path_region)
        else: 
            source_region = pd.DataFrame()
            sink_region = pd.DataFrame()

        if s.site != 'None':
            source_site = csv_import(source_in_path_site)
            sink_site = csv_import(sink_in_path_site)
        else:
            source_site = pd.DataFrame()
            sink_site = pd.DataFrame()

        # Compile
        out_country, out_region, out_site = forest_calculation(source_country,
                                                               source_region,
                                                               source_site,
                                                               s.country,
                                                               s.region,
                                                               s.site,
                                                               sink_country,
                                                               sink_region, 
                                                               sink_site,
                                                               s.source_emit_col,
                                                               s.sink_region_efficiency_col,
                                                               s.sink_country_efficiency_col)


        # Export 
        if s.country != 'None':
            out_country.to_csv(out_path_country, index=False)
        
        if s.region != 'None':
            out_region.to_csv(out_path_region, index=False)

        if s.site != 'None':
            out_site.to_csv(out_path_site, index=False)
 
        # Success
        print(f"\n------------------- Forest compiled -------------------\n")
        return out_country, out_region, out_site
        