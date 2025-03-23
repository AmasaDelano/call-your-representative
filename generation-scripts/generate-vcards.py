
import requests
import datetime
from munch import DefaultMunch
from PIL import Image
from pathlib import Path
import os
import io
import re
import json
import shutil
import git
import yaml
import urllib3
from vcard.vcard_validator import VcardValidator

USE_CACHED_DATA = True
OVERWRITE_IMAGES = False

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def load_json_from_url(url):
    response = requests.get(url)
    json_data = response.json()
    obj_data = DefaultMunch.fromDict(json_data)
    return obj_data

def load_json_from_file(path):
    with open(path, encoding="utf-8") as file:
        contents = file.read()
        json_data = json.loads(contents)
        obj_data = DefaultMunch.fromDict(json_data)
        return obj_data

def write_json_to_file(obj, path):
    with open(path, "w", encoding="utf-8") as file:
        file.write(json.dumps(obj, indent=4, sort_keys=True, default=str))

def get_all_state_legislators():
    # DOWNLOAD OPENSTATES PEOPLE GIT REPO
    state_repo_local_path = "./generation-scripts/temp-data/states"
    # if os.path.exists(state_repo_local_path):
    #     os.system(f"rmdir /S /Q '{state_repo_local_path}'")
    # os.mkdir(state_repo_local_path)
    # print("Cloning state member git repo...")
    # # First run these:
    # # git config --global core.longpaths true
    # git.Repo.clone_from("https://github.com/openstates/people.git", state_repo_local_path)
    # print("Done cloning state member git repo")

    # PROCESS ALL THE LEGISLATURE PEOPLE FILES
    state_members = []
    state_committees = {}

    states = {}
    with open("./generation-scripts/state-legislature-names.json", encoding="utf-8") as file:
        contents = file.read()
        states = json.loads(contents)
    for state in states.keys():
        
        # LOAD COMMITTEES
        committees_dir_path = f"{state_repo_local_path}/data/{state.lower()}/committees/"
        file_names = os.listdir(committees_dir_path)
        state_committees[state] = []
        for file_name in file_names:
            file_path = os.path.join(committees_dir_path, file_name)
            print(file_path)
            with open(file_path, encoding="utf-8") as file:
                state_committee = yaml.safe_load(file)
                state_committee = DefaultMunch.fromDict(state_committee)
                state_committees[state].append(state_committee)
                # print(state_committee)

        # LOAD LEGISLATURE
        legislature_dir_path = f"{state_repo_local_path}/data/{state.lower()}/legislature/"
        file_names = os.listdir(legislature_dir_path)
        for file_name in file_names:
            file_path = os.path.join(legislature_dir_path, file_name)
            print(file_path)
            with open(file_path, encoding="utf-8") as file:
                state_member = yaml.safe_load(file)
                state_member["state"] = state
                state_member["lower_body"] = states[state]
                state_member = DefaultMunch.fromDict(state_member)
                state_members.append(state_member)

    return (state_members, state_committees)

def clean_committee_name(name, committee_type, state):
    name = name.replace("House Committee on", "").replace("Senate Committee on", "").replace("Joint Committee on", "").replace("Committee on", "").replace("Committee", "").replace("Joint", "").replace("Legislative", "").replace("Commission on", "").replace("Permanent Subcommittee on", "").replace("House Permanent Select", "").replace("House Select", "").replace("Senate Select", "").replace("Senate Special", "").replace("United States Senate Caucus on", "").strip()
    committee_type = committee_type
    if committee_type == "joint" or (committee_type == "legislature" and state != "NE"):
        name = f"{name} (Joint)"
    name = f"{name[0].upper()}{name[1:]}"
    return name

lookup_data = {}
missing_phone_numbers = []
missing_images = []

def create_contact_card_and_lookup_data(id, first_name, last_name, nickname, official_name, gender, phone, email, rep_type, district, state_abbr, is_state, committee_names, img_url, website):
    def clean_for_filename(text):
        return text.lower().replace(" ", "-").replace(".", "")

    def clean_first_name(official_name, first_name, nickname):
        if nickname is not None:
            return nickname

        if official_name is not None:
            return official_name.split(" ")[0]

        matches = re.findall(r'\((.+?)\)', first_name)
        if len(matches) > 0:
            return matches[0]

        return first_name
    nickname = clean_first_name(official_name=official_name, first_name=first_name, nickname=nickname)

    id = id.replace("/", "_")
    rep_type = rep_type.lower()

    # CREATE CONTACT FILE
    chamber = "Legislature"
    role = "Representative"
    rep_type_abbr = "rep"
    if rep_type in ("sen", "upper", "legislature"):
        chamber = "Senate"
        role = "Senator"
        rep_type_abbr = "sen"
    elif rep_type in ("rep", "lower", "house"):
        chamber = "House"
        role = "Representative"
        rep_type_abbr = "rep"
    elif rep_type in ("assembly"):
        chamber = "Assembly"
        role = "Assembly Member"
        rep_type_abbr = "assembly"
    elif rep_type in ("delegate"):
        chamber = "House"
        role = "Delegate"
        rep_type_abbr = "delegate"
    else:
        raise Exception(f"New rep_type found: {rep_type}")
    
    if is_state:
        chamber = f"{state_abbr} {chamber}"
    else:
        chamber = f"US {chamber}"
    
    tagline = f"US {role} for {state_abbr}"
    if is_state:
        tagline = f"{role} in {state_abbr} Legislature\\, District {district}"
    elif rep_type != "sen":
        tagline = f"US Congress, Representative from {state_abbr}\\, District {district}"
    
    committee_entries = ""
    possessive_subject_pronoun = "they're"
    if gender == "F":
        possessive_subject_pronoun = "she's"
    elif gender == "M":
        possessive_subject_pronoun = "he's"
    if len(committee_names) > 0:
        committee_entries = f"\\n\\nCommittees {possessive_subject_pronoun} on:\\n- {"\\n- ".join(committee_names)}"

    file_name = f"{clean_for_filename(nickname)}-{clean_for_filename(last_name)}-{rep_type_abbr}-{state_abbr}"
    if phone is None:
        missing_phone_numbers.append(f"{first_name} {last_name}")
        print(f"Missing phone number for {role} {first_name} {last_name} ({id})")
        file_name = ""
    else:
        contact_file_path = f"{representatives_directory}/{file_name}.vcf"
        with open(contact_file_path, "w", encoding="utf-8") as file:
            vcard_contents = f"""BEGIN:VCARD
VERSION:3.0
FN;CHARSET=UTF-8:{nickname} {last_name} ({chamber})
N;CHARSET=UTF-8:{last_name} ({chamber});{nickname};;;
TEL;TYPE=WORK,VOICE:{phone}
"""
            if email:
                vcard_contents += f"EMAIL;CHARSET=UTF-8;type=WORK,INTERNET:{email}"
            elif website:
                vcard_contents += f"URL;CHARSET=UTF-8:{website.replace(",", "\\,").replace(";", "\\;")}"
                
            vcard_contents += f"""
NOTE;CHARSET=UTF-8:{tagline}{committee_entries}\\n\\n(Created {datetime.date.today()}\\, update info at CallYourRepresentative.us)
REV:{datetime.datetime.now().isoformat()}
END:VCARD"""
            file.write(vcard_contents)
            validator = VcardValidator(contact_file_path, True)
            # print(validator.result)

        print(f"Created contact file {file_name} ({id})")

    # DOWNLOAD HEADSHOT
    img_filepath = f"{representatives_directory}/../pics/{id}.jpg"
    img_found = os.path.exists(img_filepath)
    if img_url is not None and (OVERWRITE_IMAGES or not img_found):
        try:
            img_from_url = requests.get(img_url, verify=False, timeout=30)
            img_data = io.BytesIO(img_from_url.content)
            img = Image.open(img_data)
            img = img.convert("RGB")
            new_height = 250
            new_width = int((img.size[0] * new_height) / img.size[1])
            new_size = (new_width, new_height)
            img = img.resize(new_size, Image.LANCZOS)
            img.save(img_filepath, "JPEG")
            img_found = True
        except Exception as error:
            missing_images.append(f"{first_name} {last_name}: {img_url}")
            print(f"ERROR COULD NOT DOWNLOAD AND RESIZE IMAGE FROM {img_url} to {img_filepath}: {error}")

    # CREATE LOOKUP DATA FOR WEBSITE
    lookup_data[id] = {
        "id": id,
        "first_name": first_name,
        "last_name": last_name,
        "gender": gender,
        "rep_type": rep_type_abbr,
        "state": state_abbr,
        "district": district,
        "is_state": is_state,
        "contact_file": file_name,
        "img_found": img_found,
        "website": website
    }

# Delete all representative vcards.
representatives_directory = "./dist/representatives/vcards"
if os.path.exists(representatives_directory):
    shutil.rmtree(representatives_directory)
vcards_path = Path(representatives_directory)
vcards_path.mkdir(parents=True, exist_ok=True)
pic_directory = f"{representatives_directory}/../pics"
if OVERWRITE_IMAGES and os.path.exists(pic_directory):
    shutil.rmtree(pic_directory)
if not os.path.exists(pic_directory):
    os.mkdir(pic_directory)


# PROCESS REPRESENTATIVES FOR STATES

temp_data_dir = "./generation-scripts/temp-data/"
state_members = []
state_committees = {}
if not USE_CACHED_DATA:
    (state_members, state_committees) = get_all_state_legislators()
    print (f"About to write {len(state_members)} state rep and committee records!")
    if len(state_members) > 0:
        write_json_to_file(state_members, f"{temp_data_dir}state_reps.json")
    if len(state_committees) > 0:
        write_json_to_file(state_committees, f"{temp_data_dir}state_committees.json")
if len(state_members) == 0:
    state_members = load_json_from_file(f"{temp_data_dir}state_reps.json")
print(f"State members: {len(state_members)}")
if len(state_committees) == 0:
    state_committees = load_json_from_file(f"{temp_data_dir}state_committees.json")
print(f"State committees: {len(state_committees)}")

for member in state_members:
    gender = ""
    if member.gender == "Male":
        gender = "M"
    elif member.gender == "Female":
        gender = "F"

    state_abbr = member.state

    website=""
    if member.links is not None and len(member.links) > 0:
        website=member.links[0].url

    rep_type = member.roles[0].type
    if rep_type == "lower":
        rep_type = member.lower_body.lower()

    phone = None
    if member.offices is not None and len(member.offices) > 0:
        phone = member.offices[0].voice

    def get_matching_committee(committee):
        return any(m.person_id == member.id for m in committee.members)
    matching_committees = filter(get_matching_committee, state_committees[state_abbr])
    def get_committee_name(committee):
        return clean_committee_name(committee.name, committee.chamber, member.state)
    committee_names = list(map(get_committee_name, matching_committees))

    create_contact_card_and_lookup_data(
        id=member.id,
        first_name=member.given_name,
        last_name=member.family_name,
        nickname=None,
        official_name=member.name,
        gender=gender,
        phone=phone,
        email=member.email,
        rep_type=rep_type,
        district=member.roles[0].district,
        state_abbr=state_abbr,
        is_state=True,
        committee_names=committee_names,
        img_url=member.image,
        website=website)


# PROCESS REPRESENTATIVES FOR US CONGRESS

members = []
committees = []
committee_membership = []
if not USE_CACHED_DATA:
    members = load_json_from_url("https://unitedstates.github.io/congress-legislators/legislators-current.json")
    write_json_to_file(members, f"{temp_data_dir}legislators-current.json")
    committees = load_json_from_url("https://unitedstates.github.io/congress-legislators/committees-current.json")
    write_json_to_file(committees, f"{temp_data_dir}committees-current.json")
    committee_membership = load_json_from_url("https://unitedstates.github.io/congress-legislators/committee-membership-current.json")
    write_json_to_file(committee_membership, f"{temp_data_dir}committee-membership-current.json")
else:
    members = load_json_from_file(f"{temp_data_dir}legislators-current.json")
    committees = load_json_from_file(f"{temp_data_dir}committees-current.json")
    committee_membership = load_json_from_file(f"{temp_data_dir}committee-membership-current.json")

unique_committee_names = {}
for member in members:
    current_term = member.terms[-1]
    
    def find_matching_committee_thomas_id(committee_key):
        committee = committee_membership[committee_key]
        return any(membership.bioguide == member.id.bioguide for membership in committee)
    committee_thomas_ids = list(filter(find_matching_committee_thomas_id, committee_membership))

    def find_committee_name(committee_key):
        matching_committees = filter(lambda c: committee_key.startswith(c.thomas_id), committees)
        committee = None
        def find_matching_committee():
            for matching_committee in matching_committees:
                if committee_key == matching_committee.thomas_id:
                    return matching_committee
                for subcommittee in matching_committee.subcommittees:
                    if matching_committee.thomas_id + subcommittee.thomas_id == committee_key:
                        return subcommittee
        matching_committee = find_matching_committee()
        name = clean_committee_name(matching_committee.name, matching_committee.type, member.state)
        unique_committee_names[name] = ""
        return name
    committee_names = list(map(find_committee_name, committee_thomas_ids))
    # print(f"{member.name.last} of {current_term.state}: {committee_names}")

    create_contact_card_and_lookup_data(
        id=member.id.bioguide,
        first_name=member.name.first,
        last_name=member.name.last,
        nickname=member.name.nickname,
        official_name=member.name.official_full,
        gender=member.bio.gender,
        phone=current_term.phone,
        email="",
        rep_type=current_term.type,
        district=current_term.district,
        state_abbr=current_term.state,
        is_state=False,
        committee_names=committee_names,
        img_url=f"https://unitedstates.github.io/images/congress/225x275/{member.id.bioguide}.jpg",
        website=current_term.contact_form or current_term.url)

print("\n".join(unique_committee_names))

write_json_to_file(lookup_data, f"./src/data/rep_lookup.json")
write_json_to_file(missing_phone_numbers, f"./src/data/missing_phone_numbers.json")
write_json_to_file(missing_images, f"./src/data/missing_images.json")
