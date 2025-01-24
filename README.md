# Emission-Estimation-Using-Emission-Events
This repository is created to demonstrate the process of estimating emissions using emission events.
![Sankey Chart](https://github.com/user-attachments/assets/ff045a6c-9c3a-4a8d-8939-03231d9506c3)

More details about this study can be found in Gao et al., 2025: doi 

# Both jupyter notebooks and excel/csv files are by case study 

## Case study 1: 
![reconciled_results_case_study_1](https://github.com/user-attachments/assets/401e48cc-367f-4f35-b3a7-86718d8ba936)

### Input data files 
- **Sample_site_simulated_observations_case_1.xlsx**: 146 Synthetic emission observations, inlcuding 89 CMS measurements, 4 flyover survey records , 4 OGI inspection records and 49 venting data points.
- **Sample_leak_rate.csv**: component-scale leak rates from datasets organized by Rutherford et al., 2021
- **weather_permian.nc**: weather data in permian basin downloaded from ERA5
  
### notebooks: 
- **Emission_observations_to_emission_events_case_study_1.ipynb** -> Creating emission events by using emission observations in Sample_site_simulated_observations_case_1.xlsx.
- **Estimate_duration_and_rate_uncertainty_for_PRE_case_study_1.ipynb** -> Demonstrating how LPR and NRR can be used to simulate the duraton uncertainty for partially resolved events.
- **Emissions_from_unresolved_events_case_study_1.ipynb** -> Demonstrating how Johnson et al., (2023) can be integrated into emission event framewokr to simulate emissions from unresolved events.
-  **Event_sankey_diagram_case_study_1.ipynb** -> create sankey diagram of emission observation and emission events.
-  **Plot_results_case_study_1.ipynb** -> Plot bar charts of emissions from RE, PRE, and UE. 

 ### Output data file: 
 - **merged_observations_case_study_1.csv**: Emission events initialized from 146 Synthetic emission observations.
 - **merged_events_case_study_1.csv**: Emission events after merged by following time algebra and spatial correlation.
 - **events_with_uncertianty_case_study_1.csv**: Emission events (only REs and PREs) with uncertainties.

 ## Case study 2: 
 ![reconciled_results_case_study_2](https://github.com/user-attachments/assets/7cd28820-369d-4b06-8ac6-e9a0795e3da2)

 ### Input data files 
 - **Sample_site_simulated_observations_case_1.xlsx**: 36 Synthetic CMS observations.

### notebooks: 
- **Bootstrap_unresolved_events_case_study_2.ipynb** -> Creating emission events by suing 36 CMS observations and also bootstrapping emissions from unresolved events.
- **Plot_results_case_study_2.ipynb** -> Plot bar charts of emissions from RE, PRE, and UE.

### Output data file: 
 - **events_with_uncertianty_case_study_2.csv**: Emission events with uncertainties.
   
