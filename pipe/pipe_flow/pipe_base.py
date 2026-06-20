import logging 
import os 
import yaml 

from dataclasses import dataclass
from abc import ABC, abstractmethod

#//////////////////////////////////
#          CONFIGURATION           
#//////////////////////////////////

@dataclass
class Config:

#Variables

    #Filters
    country: str
    sector: str
    region: str
    site: str

    # Values
    gas: str
    limit: str
    year: str
    threshold: str

    # Paths
    out_csv_path: str
    out_fig_path: str
    in_csv_path: str

    # API
    source_api_url: str
    url_region_api: str
    language_region_api: str #??

    # Columns: 
    source_id_col: str
    source_emit_col: str
    source_lat_col: str
    source_lon_col: str
    source_name_col: str
    source_country_col: str
    source_region_col: str

    sink_country_col: str
    sink_region_col: str
    sink_site_col: str
    sink_cover_col: str
    sink_intake_col: str
    sink_threshold_col: str
    sink_region_efficiency_col: str
    sink_cover_country_col: str
    sink_intake_country_col: str
    sink_country_efficiency_col: str

    # Files
    source_raw: str
    sink_raw: str
    forest_country: str
    forest_region: str
    forest_result: str
    forest_full: str

    @classmethod
    def from_dict(cls, data):
        return cls(**data)
    

#//////////////////////////////////
#          PARSE CONFIG           
#//////////////////////////////////

def parse_config():
    pipeline_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(os.path.dirname(pipeline_dir), "config")

    base_config = os.path.join(config_path, "base.yaml")
    with open(base_config, "r") as file:
        data = yaml.load(file, Loader=yaml.FullLoader)

    input_config = os.path.join(config_path, "case.yaml")
    if os.path.exists(input_config):
        with open(input_config, "r") as file:
            data_input = yaml.load(file, Loader=yaml.FullLoader)
        data.update(data_input)

    config = Config.from_dict(data)
    return config


#//////////////////////////////////
#             PIPE BASE           
#//////////////////////////////////

class PipelineBase(ABC):
    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = parse_config()

    @abstractmethod
    def run(self):
        pass
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = parse_config()

    @abstractmethod
    def run(self):
        pass
