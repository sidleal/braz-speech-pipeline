# BrazSpeechData Pipeline Script

## Introduction
This script is designed to run data pipelines for diarization, transcription, and metadata extraction, specifically for feeding the BrazSpeechData platform. It includes functionalities for exporting corpus datasets and transcribing audio files.

## Installation
The script uses Poetry for dependencies management, and keep in mind that the Dockerized version **ISN'T** working. In order to start using this project, follow the steps bellow:

#### 1. Clone and create venv
First, clone the repo to your desired folder.
```Bash
git clone https://github.com/nilc-nlp/braz-speech-pipeline.git
```
Then create a virtual environment to hold the dependencies, with
```Bash
cd braz-speech-pipeline
python -m venv .venv
source .venv/bin/activate
```

#### 2. Install your dependencies
> Attention! This project needs Python 3.8 or higher to work.

Install the required dependencies by running:
```
poetry install
```

If you need to add new dependencies, run:
```
poetry add <dependency>
```

#### 3. Google Drive Token
In order to use the Google Drive API, you need to create a token file, similar to the one in `example.token.json`. To do so, follow the steps on [this link](https://cloud.google.com/iam/docs/service-accounts-create) and save the file as `token.json` in the root folder of this project.

This step is necessary to access the raw files on Google Drive. If you don't need to access the raw files, you can skip this step. 

## Usage
To use this script, navigate to the directory where the script is located and run:

```Bash
poetry run python main.py [COMMAND] [OPTIONS]
```


Replace `[COMMAND]` with one of the commands listed below, and choose between the available options.

If you need any help, run:
```Bash
poetry run python main.py --help
```
or
```Bash
poetry run python main.py [COMMAND] --help
```

## Command Guide

### Export Command

#### Options
Use this command to export corpus datasets in various formats.

| Option | Description | Type | Default | Required |
| ------ | ----------- | ---- | ------- | -------- |
| `--corpus_id` | Corpus ID | int | None | Yes |
| `--output-folder` | Output folder | Path | './data/export' | No |
| `--export-audio-to-formats` | List of audio formats to export (e.g., wav, mp3) | List[AudioFormat] | ["wav", "mp3"] | No |
| `--sample-rate` | Sample rate for audio export | int | 48000 | No |
| `--google-drive-folder-ids` | List of Google Drive folder IDs for source audios | List[str] | None | No |
| `--filter-format` | Specify which files format to read from Google Drive | AudioFormat | None | No |
| `--original-audios` | Whether to export original audios | bool | False | No |
| `--csv` | Export data to CSV format | bool | False | No |
| `--continuous-text` | Export concatenated text from audio segments | bool | False | No |
| `--speakers-text` | Export text files organized by speaker | bool | False | No |
| `--json-metadata` | Export audio metadata in JSON format | bool | False | No |
| `--textgrid` | Export data in TextGrid format for use with Praat | bool | False | No |
| `--all` | Export all data | bool | False | No |
| `--debug` | When activated, will export only 10 audios | bool | False | No |

#### Running the command

To run the export script, you should use the base command
```
poetry run python main.py export [OPTIONS]
```

Then you can specify which data to export by using the options listed above. For example, to export all data from MUPE (corpus 1), run:
```
poetry run python main.py export --corpus_id 1 --all --google-drive-folder-ids ID_OF_FOLDER_ON_DRIVE --export-audio-to-formats mp3 --debug
```

If you want everything, but the original audios, you can run:
```
poetry run python main.py export --corpus_id 1 --csv --textgrid --continuous-text --speakers-text --json-metadata --debug 
```

If you need any help, run:
```Bash
poetry run python main.py export --help
```
#### Export types

##### CSV
This command will create an export of the entire database in CSV format. It will export on file `corpus_{corpus_id}_audios.csv` and another one `corpus_{corpus_id}_segments.csv`. The first, contains a list of all audios inside the corpus, with their metadata. The second, contains a list of all segments for each audio, with their metadata, the ASR transcription and the final transcription. For this last one, it's also exported a `.parquet` file for faster loading.

##### Continuous Text
This command will create a text file for each audio, containing the concatenated text of all segments. The text files will be saved in a folder named `{audio_name}_concatenated_text.txt` inside the output folder.

##### Speakers Text
This command will create a text file for each audio, containing the text of each segment, organized by speaker. The text files will be saved in a folder named `{audio_name}_by_speaker.txt` inside the output folder.

##### JSON Metadata
This command will create a JSON file for each audio, containing the metadata of the audio. The JSON files will be saved in a folder named `{audio_name}_metadata.json` inside the output folder.

##### TextGrid
This command will create a TextGrid file for each audio, containing the metadata of the audio. The TextGrid files will be saved in a folder named `{audio_name}.textgrid` inside the output folder.

##### Original Audios
This command will create a copy of the original audios, in the format specified by the `export-audio-to-formats` option. The audios will be saved in a folder named `original_audios` inside the output folder. You can also specify the final `sample-rate` for the audios.

### Transcribe Command
This script provides functionalities for transcribing audio files using the WhisperX library. It supports various features like diarization, speaker identification, and alignment of transcribed segments with audio, specifically tailored for processing audio datasets.

#### Options
Use this command to transcribe audio files from specified Google Drive folders.

| Option                    | Description                                                           | Type      | Required | Default    |
|---------------------------|-----------------------------------------------------------------------|-----------|----------|------------|
| `--corpus-id`               | Unique identifier for the corpus                                      | int       | Yes      | None       |
| `--folder-ids`              | List of Google Drive folder IDs containing audio files                | List[str] | Yes      | None       |
| `--output_folder`           | Directory path for saving the output                                  | Path      | No      | "./data/"       |
| `--storage-output-folder-id`                      | Instance of Database for database operations                          | Google Drive folder ID to save the transcriptions. If none is provided, the transcriptions will be saved in the same folder as the │
│                                                                            audios.  | No       | None       |
| `--format-filter `    | Filter audios by format                        | [wav|mp4|mp3]  | No    | None       |
| `--save-to-drive`           | Flag to save transcriptions to Google Drive                           | bool      | No       | False      |
| `--save-to-db`        | Flag to save transcriptions to database                                | bool      | No       | False      |
| `--transfer-to-server`     | Flag to transfer transcriptions to server                              | bool      | No       | False      |
| `storage_output_folder_id`| Google Drive folder ID for storing transcriptions                     | str       | No       | None       |

#### Running the command

To run the transcribe script, you should use the base command
```
poetry run python main.py transcribe --corpus_id [CORPU_ID] --folder_ids [IDs] [OPTIONS]
```

You can choose between the flags: `--save-to-drive`, `--save-to-db` and `--transfer-to-server`. The first one will upload the segments and transcription files back to GoogleDrive, the second will insert the entries on the BrazSpeechPlatform database, and the third will transfer the files to the server, to make them available on the platform.

If you need any help, run:
```Bash
poetry run python main.py transcribe --help
```

## Future improvements
- [ ] `feat` add support for other ASR services
- [ ] `feat` add support for other Repositories other than Google Drive
- [ ] `fix` Dockerfile for running the script
- [ ] `refact` inject dependencies on the script for better modularity
- [ ] `tests` add unit tests for the script

