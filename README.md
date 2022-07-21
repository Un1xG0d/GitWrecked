# GitWrecked
Scan recent GitHub commits and generate a report on any leaked secrets.

## Setup
```
pip3 install -r requirements.txt
touch reset.log
touch scanned_repos.txt
```

## Usage
This script takes a GitHub topic as an argument. You can find the complete list of topics [here](https://github.com/topics). If a topic is not specified, the default value is "all".

```
python3 gitwrecked.py --topic api
```