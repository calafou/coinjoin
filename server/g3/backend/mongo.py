from pymongo import Connection

client = Connection('localhost', 27017)
db = client.test_database

import json

from bson.objectid import ObjectId
from datetime import datetime

class Encoder(json.JSONEncoder):
    def default(self, o):
        if o.__class__ == datetime:
            return o.ctime()
        elif o.__class__ == ObjectId:
            return str(o)
        return json.JSONEncoder.default(self, o)

# monkey patch json.dumps
#json._dumps = json.dumps
#json.dumps = lambda o, cls=None: json._dumps(o, cls=Encoder)


def query_db(query):
    post = {"author": "Mike",
         "text": "My first blog post!",
         "tags": ["mongodb", "python", "pymongo"],
         "date": datetime.utcnow()}

    posts = db.posts


    #post_id = posts.insert(post)

    #print db.collection_names()

    a = posts.find_one({'tags': query})

    #for post in posts.find():
    #   print post
    return a
