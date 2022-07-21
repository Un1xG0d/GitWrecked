import argparse
import io
import json
import requests
import sys
import time
from bs4 import BeautifulSoup
from datetime import datetime
from playsound import playsound
from truffleHog import truffleHog

def collect_all_urls():
	all_links = []
	topics = ["3D", "Ajax", "Algorithm", "Amp", "Android", "Angular", "Ansible", "API", "Arduino", "ASP.NET", "Atom", "Awesome Lists", "Amazon Web Services", "Azure", "Babel", "Bash", "Bitcoin", "Bootstrap", "Bot", "C", "Chrome", "Chrome extension", "Command line interface", "Clojure", "Code quality", "Code review", "Compiler", "Continuous integration", "COVID-19", "C++", "Cryptocurrency", "Crystal", "C#", "CSS", "Data structures", "Data visualization", "Database", "Deep learning", "Dependency management", "Deployment", "Django", "Docker", "Documentation", ".NET", "Electron", "Elixir", "Emacs", "Ember", "Emoji", "Emulator", "ESLint", "Ethereum", "Express", "Firebase", "Firefox", "Flask", "Font", "Framework", "Front end", "Game engine", "Git", "GitHub API", "Go", "Google", "Gradle", "GraphQL", "Gulp", "Hacktoberfest", "Haskell", "Homebrew", "Homebridge", "HTML", "HTTP", "Icon font", "iOS", "IPFS", "Java", "JavaScript", "Jekyll", "jQuery", "JSON", "The Julia Language", "Jupyter Notebook", "Koa", "Kotlin", "Kubernetes", "Laravel", "LaTeX", "Library", "Linux", "Localization", "Lua", "Machine learning", "macOS", "Markdown", "Mastodon", "Material design", "MATLAB", "Maven", "Minecraft", "Mobile", "Monero", "MongoDB", "Mongoose", "Monitoring", "MvvmCross", "MySQL", "NativeScript", "Nim", "Natural language processing", "Node.js", "NoSQL", "npm", "Objective-C", "OpenGL", "Operating system", "P2P", "Package manager", "Parsing", "Perl", "Phaser", "PHP", "PICO-8", "Pixel Art", "PostgreSQL", "Project management", "Publishing", "PWA", "Python", "Qt", "R", "Rails", "Raspberry Pi", "Ratchet", "React", "React Native", "ReactiveUI", "Redux", "REST API", "Ruby", "Rust", "Sass", "Scala", "scikit-learn", "Software-defined networking", "Security", "Server", "Serverless", "Shell", "Sketch", "SpaceVim", "Spring Boot", "SQL", "Storybook", "Support", "Swift", "Symfony", "Telegram", "Tensorflow", "Terminal", "Terraform", "Testing", "Twitter", "TypeScript", "Ubuntu", "Unity", "Unreal Engine", "Vagrant", "Vim", "Virtual reality", "Vue.js", "Wagtail", "Web Components", "Web app", "Webpack", "Windows", "WordPlate", "WordPress", "Xamarin", "XML"]
	for github_topic in topics:
		print("[!] Gathering URLs for topic: " + github_topic)
		page = requests.get("https://github.com/topics/" + github_topic + "?o=desc&s=updated")
		soup = BeautifulSoup(page.content, "html.parser")
		links = [a.get("href") for a in soup.findAll("a", {"class":"text-bold wb-break-word"})]
		for url in links:
			all_links.append("https://github.com" + url)
	return all_links

def collect_urls(github_topic):
	page = requests.get("https://github.com/topics/" + github_topic + "?o=desc&s=updated")
	soup = BeautifulSoup(page.content, "html.parser")
	links = [a.get("href") for a in soup.findAll("a", {"class":"text-bold wb-break-word"})]
	for url in links:
		links[links.index(url)] = "https://github.com" + url
	return links

def generate_report(repo_url):
	timestamp = datetime.now().strftime("%m-%d-%Y %I:%M %p")
	repo_name = repo_url.split("/")[-1]
	repo_username = repo_url.split("/")[-2]
	
	f = open("reports/template.html", "r")
	report_html = f.read()
	f.close()

	secrets = scan_repo(repo_url)

	if len(secrets) != 0:
		report_html = report_html.replace("###REPO_URL###", repo_url)
		report_html = report_html.replace("###SECRETS_COUNT###", str(len(secrets)))
		report_html = report_html.replace("###SCAN_TIMESTAMP###", timestamp)

		accordion_html = ""
		for secret in secrets:
			idx = secrets.index(secret) + 1
			formatted_strings = ""
			for string in secret["strings"]:
				formatted_strings += string + "<br>"
			if idx == 1:
				accordion_html += """<div class="card"><div class="card-header" id="heading""" + str(idx) + """"><h5 class="mb-0"><button class="btn btn-link" type="button" data-toggle="collapse" data-target="#collapse""" + str(idx) + """" aria-expanded="true" aria-controls="collapse""" + str(idx) + """">""" + secret["reason"] + """</button></h5></div><div id="collapse""" + str(idx) + """" class="collapse show" aria-labelledby="heading""" + str(idx) + """" data-parent="#secretsAccordion"><div class="card-body"><b>Filename: </b>""" + secret["path"] + """<br><b>Commit: </b>""" + secret["commit"] + """<br><b>Date: </b>""" + secret["date"] + """<br><b>Branch: </b>""" + secret["branch"] + """<br><b>Strings: </b><br>""" + formatted_strings + """<br><a href=" """ + repo_url + "/commit/" + secret["commitHash"] + """">View commit</a></div></div></div>"""
			else:
				accordion_html += """<div class="card"><div class="card-header" id="heading""" + str(idx) + """"><h5 class="mb-0"><button class="btn btn-link" type="button" data-toggle="collapse" data-target="#collapse""" + str(idx) + """" aria-expanded="true" aria-controls="collapse""" + str(idx) + """">""" + secret["reason"] + """</button></h5></div><div id="collapse""" + str(idx) + """" class="collapse" aria-labelledby="heading""" + str(idx) + """" data-parent="#secretsAccordion"><div class="card-body"><b>Filename: </b>""" + secret["path"] + """<br><b>Commit: </b>""" + secret["commit"] + """<br><b>Date: </b>""" + secret["date"] + """<br><b>Branch: </b>""" + secret["branch"] + """<br><b>Strings: </b><br>""" + formatted_strings + """<br><a href=" """ + repo_url + "/commit/" + secret["commitHash"] + """">View commit</a></div></div></div>"""
		report_html = report_html.replace("###SECRETS_ACCORDION_CONTENT###", accordion_html)
		f = open("reports/exports/" + repo_username + "_" + repo_name + ".html", "w")
		f.write(report_html)
		f.close()
		print("[!] Exported report: " + "reports/exports/" + repo_username + "_" + repo_name + ".html")
		playsound("sounds/secrets_discovered.mp3")
	else:
		print("[X] No secrets found in repo: " + repo_url)

def load_scanned_repos():
	scanned_repos = []
	f = open("scanned_repos.txt", "r")
	for line in f.readlines():
		scanned_repos.append(line.replace("\n", ""))
	f.close()
	return scanned_repos

def save_scanned_repo(repo_url):
	f = open("scanned_repos.txt", "a")
	f.write(repo_url + "\n")
	f.close()

def scan_repo(repo_url):
	excluded_reasons = ["GitHub", "High Entropy", "Password in URL"]
	secrets = []
	tmp_stdout = io.StringIO()
	bak_stdout = sys.stdout
	sys.stdout = tmp_stdout

	try:
		truffleHog.find_strings(repo_url, do_regex=True, printJson=True, surpress_output=False, max_depth=100)
	except:
		print("[X] Failed to scan repo.")
	finally:
		sys.stdout = bak_stdout

	json_result_list = tmp_stdout.getvalue().split("\n")

	if "[X] Failed to scan repo." in json_result_list[0]:
		print("[X] Failed to scan repo.")
	else:
		results = [json.loads(r) for r in json_result_list if bool(r.strip())]
		for secret in results:
			if secret["reason"] not in excluded_reasons:
				s = {}
				s["branch"] = secret["branch"]
				s["commit"] = secret["commit"]
				s["commitHash"] = secret["commitHash"]
				s["date"] = secret["date"]
				s["path"] = secret["path"]
				s["reason"] = secret["reason"]
				s["strings"] = secret["stringsFound"]
				secrets.append(s)
		return secrets

def main():
	parser = argparse.ArgumentParser(description="Scan recent GitHub commits and generate a report on any leaked secrets.")
	parser.add_argument("-t", "--topic", help="the GitHub topic to search for")
	args = parser.parse_args()

	while True:
		if args.topic == "all" or not args.topic:
			repo_urls = collect_all_urls()
		else:
			repo_urls = collect_urls(args.topic)

		print(str(repo_urls) + "\n")
		scanned_repos = load_scanned_repos()

		for repo_url in repo_urls:
			if repo_url not in scanned_repos:
				print("[!] Scanning repo: " + repo_url)
				save_scanned_repo(repo_url)
				generate_report(repo_url)
			else:
				print("[X] Already scanned repo: " + repo_url)
		print("[!] Sleeping for 15 minutes.")
		time.sleep(900)

main()