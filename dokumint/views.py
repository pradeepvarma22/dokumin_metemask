import glob
from django.shortcuts import render,redirect
from dokumint.models import Certifier,Receiver,ProjectDesc
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import json
import requests

import os
from html2image import Html2Image
from django.core.files.base import File
from django.conf.urls.static import static
from utils.keys import keys
from utils.nftstorage import NftStorage
from utils.pinata import Pinata
from config.settings import BASE_DIR

NFTSTORAGE_API_KEY = keys['NFTSTORAGE']
PINATA_JWT = keys['PINATA']
base_uri = "https://ipfs.io/ipfs/"

# Create your views here.
def Home(request):
    return render(request,'home.html')


def Validate(request):
    if request.POST:
        wallet_address = request.POST.get('wallet_address')
        moralis_user_id = request.POST.get('moralis_user_id')
        request.session['wallet_address'] = wallet_address
        request.session['moralis_user_id'] = moralis_user_id

        certifier= Certifier()
        certifier.address = wallet_address
        certifier.moralisid = moralis_user_id
        certifier.save()

        return redirect('dashboard',moralis_user_id)
    else:
        return redirect('home')


def dashboard(request,id):
    
    return render(request,'dashboard.html')

def checkMe(request):
    wallet_address=request.session['wallet_address']
    moralis_user_id=request.session['moralis_user_id']
    if request.POST:
        name = request.POST.get('name')
        symbol = request.POST.get('symbol')
        desc = request.POST.get('desc')
        csvf = request.FILES['csvf']

        certifier = Certifier.objects.get(moralisid=moralis_user_id)
        certifier.name = name
        certifier.save()

        projectdesc = ProjectDesc()
        projectdesc.certifier = certifier
        projectdesc.proj_name = name
        projectdesc.proj_desc = desc
        projectdesc.symbol = symbol

        projectdesc.save()
        df = pd.read_csv(csvf)
        df = df.reset_index()

        imgs = []

        for index, i in df.iterrows():
            obj = Receiver()
            obj.name = i['Name'] 
            obj.certifier = certifier
            obj.address = i['Address']
            obj.course = i['Course'] 

            html_template_file = open('data.txt','rt')
            data = html_template_file.read()
            data = data.replace('user_name_var',obj.name )
            data = data.replace('completion_course_var',obj.course)
            data = data.replace('Certified_by_var',certifier.name)
            html_template_file.close()

            html_template_file = open('certificate.html','wt')
            html_template_file.write(data)
            html_template_file.close()

            try:
                os.mkdir('./images/{}/'.format(certifier.name))
            except:
                pass

            try:
                os.mkdir('./metadata/{}/'.format(certifier.name))
            except:
                pass
            
            hti = Html2Image()
            with open('certificate.html') as f:
                hti.screenshot(f.read(), save_as='{}.png'.format(certifier.name+str(index+1)))

            outfile = Image.open('{}.png'.format(certifier.name+str(index+1)))
            img_path = '/images/{}/{}.png'.format(certifier.name,str(index+1))
            outfile.save('.'+ img_path)  
            obj.image = File(outfile)
            imgs.append(img_path)
            
            metafiles = []
            meta = []

            att1 = {"trait_type": "Receiver", "value":obj.name}
            att2 = {"trait_type": "Course", "value":obj.course}
            att3 = {"trait_type": "Certifier", "value":certifier.name}

            meta.append(att1)
            meta.append(att2)
            meta.append(att3)

            token = {
                "image": base_uri + str(index+1) + '.png',
                "tokenId": str(index+1),
                "name": name+ ' ' + "#" + str(index+1),
                "attributes": meta
            }

            meta_path  = '/metadata/{}/'.format(certifier.name)
            meta_file = '.' + meta_path + str(index+1) + '.json'
            metafiles.append(meta_file)

            with open(meta_file, 'w') as outfile:
                json.dump(token, outfile, indent=4)

            obj.save()        
    return render(request,'success.html',{'certifier':certifier.name, 'images':imgs})


def uploadIPFS(request):
    user = request.session['moralis_user_id']
    certifierobj = Certifier.objects.get(moralisid=user)
    receiverobj = Receiver.objects.filter(certifier=certifierobj)
    projobj = ProjectDesc.objects.get(certifier=certifierobj)
    base_img_path = './images/{}/'.format(certifierobj.name)
    base_meta_path = './metadata/{}/'.format(certifierobj.name)

    nstorage = {}
    c = NftStorage(NFTSTORAGE_API_KEY)
    imgpaths = []
    metapaths = []

    print(len(receiverobj))
    for i in range(1,len(receiverobj)+1):
        imgpaths.append(base_img_path + str(i) + '.png')
        metapaths.append(base_meta_path + str(i) + '.json')
      
    cid = c.upload(imgpaths, 'image/png')
    nstorage['image_directory_cid'] = cid

    projobj.img_hash = cid

    cid = c.upload(metapaths, 'application/json')
    nstorage['metadata_directory_cid'] = cid

    update_meta_cid(metapaths, cid)

    p = Pinata(PINATA_JWT)
    for k, v in nstorage.items():
        name = projobj.proj_name + ' ' + k.split('_')[0]
        p.pin(name, v)

    projobj.meta_hash = cid
    projobj.save()
    contract  = getContract()
    ipfs_url = "ipfs://" + cid

    contract = contract.replace('MyToken',projobj.proj_name)
    contract = contract.replace('MTK',projobj.symbol)
    contract = contract.replace('ipfs_url',"'"+ipfs_url+"'")

    return render(request, "deploy.html",  {'contract':contract, 'proj':projobj, 'ipfs_url':ipfs_url })


def update_meta_cid(file, cid):
    for i in file:
        with open(i) as f:
             data = json.load(f)
             img_file = data['image'].replace(base_uri, '')
             data['image'] = base_uri + cid + '/' + img_file
        
        with open(i, 'w') as outfile:
            json.dump(data, outfile, indent=4)    



def deploy(request):
    address = request.session['wallet_address']
    user = request.session['moralis_user_id']
    certifierobj = Certifier.objects.get(certifier=user)
    project = ProjectDesc.objects.get(certifier=certifierobj)

    url = "https://api.nftport.xyz/v0/contracts"
    payload = "{\n  \"chain\": \"polygon\",\n  \"name\": \"CRYPTOPUNKS\",\n  \"symbol\": \"CYBER\",\n  \"owner_address\":wallet,\n  \"metadata_updatable\": false,\n  \"type\": \"erc721\"\n}"
    
    payload = payload.replace('CRYPTOPUNKS',project.proj_name)
    payload = payload.replace('CYBER',project.symbol)
    payload = payload.replace('wallet','"'+address+'"')

    headers = {
        'Content-Type': "application/json",
        'Authorization': "d775b8ce-a5b7-420b-b818-3e7c46075ab2"
    }

    response = requests.request("POST", url, data=payload, headers=headers)

    print(response)
    return render(request,'response.html',{'respose':response.text})



def getContract():
    return '''
        // SPDX-License-Identifier: MIT
        pragma solidity ^0.8.4;

        import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
        import "@openzeppelin/contracts/access/Ownable.sol";

        contract MyToken is ERC721, Ownable {
            constructor() ERC721("MyToken", "MTK") {}

            function _baseURI() internal pure override returns (string memory) {
                return ipfs_url;
            }

            function safeMint(address to, uint256 tokenId) public onlyOwner {
                _safeMint(to, tokenId);
            }
        }
    '''

