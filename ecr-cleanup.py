from __future__ import print_function

import argparse
import os
import re
import boto3

REGION = None
DRYRUN = None
IMAGES_TO_KEEP = None
IGNORE_TAGS_REGEX = None


def initialize():
    global REGION
    global DRYRUN
    global IMAGES_TO_KEEP
    global IGNORE_TAGS_REGEX

    REGION = os.environ.get('REGION', "None")
    DRYRUN = os.environ.get('DRYRUN', "false").lower()
    if DRYRUN == "false":
        DRYRUN = False
    else:
        DRYRUN = True
    IMAGES_TO_KEEP = int(os.environ.get('IMAGES_TO_KEEP', 100))
    IGNORE_TAGS_REGEX = os.environ.get('IGNORE_TAGS_REGEX', "^$")


def lambda_handler(event, context):
    initialize()
    # select the aws regions
    if REGION == "None":
        ec2_client = boto3.client('ec2')
        available_regions = ec2_client.describe_regions()['Regions']
        for region in available_regions:
            # call the delete image against the region
            discover_delete_images(region['RegionName'])
    else:
        discover_delete_images(REGION)


def discover_delete_images(regionname):
    print("Discovering images in " + regionname)
    # ecr boto3 object
    ecr_client = boto3.client('ecr', region_name=regionname)

    repositories = []
    describe_repo_paginator = ecr_client.get_paginator('describe_repositories')
    # select ecr describe repos
    for response_listrepopaginator in describe_repo_paginator.paginate():
        for repo in response_listrepopaginator['repositories']:
            repositories.append(repo)

    for repository in repositories:
        if repository['repositoryUri'] == "405926721543.dkr.ecr.eu-west-2.amazonaws.com/shopify-react":
            print("------------------------")
            print("Starting with repository :" + repository['repositoryUri'])
            deletesha = []
            deletetag = []
            tagged_images = []

            describeimage_paginator = ecr_client.get_paginator('describe_images')
            for response_describeimagepaginator in describeimage_paginator.paginate(
                    registryId=repository['registryId'],
                    repositoryName=repository['repositoryName']):
                for image in response_describeimagepaginator['imageDetails']:
                    if 'imageTags' in image:
                        tagged_images.append(image)
                    else:
                        append_to_list(deletesha, image['imageDigest'])

            print("Total number of images found: {}".format(len(tagged_images) + len(deletesha)))
            print("Number of untagged images found {}".format(len(deletesha)))
            



            tagged_images.sort(key=lambda k: k['imagePushedAt'], reverse=True)


            print("Number of tagged images found: {}".format(len(tagged_images)))


            # development regex rule
            development_regex = re.compile('development')
            # staging regex rule
            staging_regex = re.compile('staging')
            # semver tag regex rule
            semver_regex = re.compile('\d+\.\d+\.\d+[-.]?')
            production_regex = re.compile('production')
            release_regex = re.compile('release')
            master_regex = re.compile('master')
            feature_regex = re.compile("feature|hot|bug|bjs|integration|snyk", re.I)

            development_list=[]
            staging_list=[]
            feature_list=[]
            production_list=[]
            release_list=[]
            semver_list=[]
            master_list=[]

            

            for image in tagged_images:
                for tag in image['imageTags']:
                    if ('master' not in tag or 'latest' not in tag) and semver_regex.search(tag) is not None and development_regex.search(tag) and staging_regex.search(tag) and feature_regex.search(tag) and production_regex.search(tag) and release_regex.search(tag) and 'production' not in tag:
                        
                        append_to_list(deletesha, image['imageDigest'])
                        append_to_tag_list(deletetag, {"imageUrl": repository['repositoryUri'] + ":" + tag,
                                                        "pushedAt": image["imagePushedAt"]})
                        print(tag)
                    if semver_regex.search(tag):
                        semver_list.append([tag, image['imageDigest']])
                    elif master_regex.search(tag):
                        master_list.append([tag, image['imageDigest']])
                    elif development_regex.search(tag):
                        development_list.append([tag, image['imageDigest']])
                    elif staging_regex.search(tag):
                        staging_list.append([tag, image['imageDigest']])
                    elif feature_regex.search(tag):
                        feature_list.append([tag, image['imageDigest']])
                    elif production_regex.search(tag):
                        production_list.append([tag, image['imageDigest']])
                    elif release_regex.search(tag):
                        release_list.append([tag, image['imageDigest']])
            all_list = semver_list[IMAGES_TO_KEEP:] + master_list[IMAGES_TO_KEEP:] + development_list[IMAGES_TO_KEEP:] + staging_list[IMAGES_TO_KEEP:] + production_list[IMAGES_TO_KEEP:] + release_list[IMAGES_TO_KEEP:] + feature_list
            for tag in all_list:
                append_to_list(deletesha, tag[1])
                append_to_tag_list(deletetag, {"imageUrl": repository['repositoryUri'] + ":" + tag[0],
                                                "pushedAt": image["imagePushedAt"]})
                print(tag[0])
                        
                        


            if deletesha:
                    print("Number of images to be deleted: {}".format(len(deletesha)))
                    delete_images(
                        ecr_client,
                        deletesha,
                        deletetag,
                        repository['registryId'],
                        repository['repositoryName']
                    )
            else:
                    print("Nothing to delete in repository : " + repository['repositoryName'])
        else:
            continue


def append_to_list(image_digest_list, repo_id):
    if not {'imageDigest': repo_id} in image_digest_list:
        image_digest_list.append({'imageDigest': repo_id})


def append_to_tag_list(tag_list, tag_id):
    if not tag_id in tag_list:
        tag_list.append(tag_id)


def chunks(repo_list, chunk_size):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(repo_list), chunk_size):
        yield repo_list[i:i + chunk_size]


def delete_images(ecr_client, deletesha, deletetag, repo_id, name):
    if len(deletesha) >= 1:
        i = 0
        for deletesha_chunk in chunks(deletesha, 100):
            i += 1
            if not DRYRUN:
                delete_response = ecr_client.batch_delete_image(
                    registryId=repo_id,
                    repositoryName=name,
                    imageIds=deletesha_chunk
                )
                print(delete_response)
            else:
                continue
    if deletetag:
        print("Image URLs that are marked for deletion:")
        for ids in deletetag:
            print("- {} - {}".format(ids["imageUrl"], ids["pushedAt"]))


if __name__ == '__main__':
    REQUEST = {"None": "None"}
    PARSER = argparse.ArgumentParser(description='Deletes stale ECR images')
    PARSER.add_argument('-dryrun', help='Prints the repository to be deleted without deleting them', default='true',
                        action='store', dest='dryrun')
    PARSER.add_argument('-imagestokeep', help='Number of image tags to keep', default='10', action='store',
                        dest='imagestokeep')
    PARSER.add_argument('-region', help='ECR/ECS region', default=None, action='store', dest='region')
    PARSER.add_argument('-ignoretagsregex', help='Regex of tag names to ignore', default="^$", action='store',
                        dest='ignoretagsregex')

    ARGS = PARSER.parse_args()
    if ARGS.region:
        os.environ["REGION"] = ARGS.region
    else:
        os.environ["REGION"] = "None"
    os.environ["DRYRUN"] = ARGS.dryrun.lower()
    os.environ["IMAGES_TO_KEEP"] = ARGS.imagestokeep
    os.environ["IGNORE_TAGS_REGEX"] = ARGS.ignoretagsregex

    # call the prune function
    lambda_handler(REQUEST, None)
    
