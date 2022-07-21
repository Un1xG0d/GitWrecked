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

def collect_all_urls(scanned_repos):
	all_links = []
	topics = ["Ansible", "API", "Amazon Web Services", "Azure", "Bash", "Bitcoin", "Bot", "Chrome", "Command line interface", "Cryptocurrency", "Database", "Deployment", "Docker", "Electron", "Ethereum", "Express", "Firebase", "Firefox", "Flask", "Git", "GitHub API", "Google", "HTTP", "iOS", "IPFS", "Java", "JavaScript", "JSON", "Jupyter Notebook", "Kubernetes", "Linux", "Mobile", "Monero", "MongoDB", "Mongoose", "Monitoring", "MySQL", "Node.js", "NoSQL", "Operating system", "P2P", "PHP", "Python", "Raspberry Pi", "REST API", "Security", "Server", "Shell", "Telegram", "Terminal", "Terraform", "Twitter", "Web app", "Windows", "WordPress"]
	for github_topic in topics:
		page = requests.get("https://github.com/topics/" + github_topic + "?o=desc&s=updated")
		soup = BeautifulSoup(page.content, "html.parser")
		links = [a.get("href") for a in soup.findAll("a", {"class":"text-bold wb-break-word"})]
		collected_urls = 0
		for url in links:
			if "https://github.com" + url not in scanned_repos:
				all_links.append("https://github.com" + url)
				collected_urls += 1
		print("[!] Collected " + str(collected_urls) + " URLs for topic: " + github_topic)
		time.sleep(1)
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

def reset_scanned_repos():
	now = datetime.now().timestamp()
	with open("reset.log", "r+") as reset_file:
		reset_timestamp = float(reset_file.read())
		print("[!] Seconds since last reset: " + str(now - reset_timestamp))
		if now - reset_timestamp > 86400:
			scanned_repos_file = open("scanned_repos.txt", "w")
			scanned_repos_file.write("")
			scanned_repos_file.close()
			reset_file.seek(0)
			reset_file.write(str(now))
			reset_file.truncate()
			print("[!] The list of scanned repos has been reset.")

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
		truffleHog.find_strings(repo_url, do_regex=True, printJson=True, surpress_output=False, max_depth=10)
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
		scanned_repos = load_scanned_repos()

		if args.topic == "all" or not args.topic:
			repo_urls = collect_all_urls(scanned_repos)
		else:
			repo_urls = collect_urls(args.topic)

		print("Total repositories collected: " + str(len(repo_urls)) + "\n")

		for repo_url in repo_urls:
			if repo_url not in scanned_repos:
				print("[!] Scanning repo: " + repo_url)
				save_scanned_repo(repo_url)
				generate_report(repo_url)
			else:
				print("[X] Already scanned repo: " + repo_url)
		reset_scanned_repos()
		print("[!] Sleeping for 30 minutes.")
		time.sleep(1800)

main()