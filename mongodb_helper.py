import pymongo
from pymongo import UpdateOne
CONNECTION_STRING = "mongodb+srv://harsh6gpt:Good1luck2@tmsearch.isqiees.mongodb.net/"


def init_mongo_connection(collection_name='trademark-master'):
    client = pymongo.MongoClient(CONNECTION_STRING)
    db = client.TMSearch
    tm_collection = db[collection_name]
    return tm_collection


def mongo_application_search(tm_collection, application_list):
    result = tm_collection.aggregate([
        {"$search": {
            "index": "application",
            "in": {
                "path": "Application Number",
                "value": application_list
            }
        }
        }
    ])
    return result


def mongo_find_one_application(tm_collection, app_num):
    result = tm_collection.find_one({'Application Number': app_num})
    return result


def mongo_one_application_search(tm_collection, app_num):
    result = tm_collection.aggregate([
        {"$search": {
            "index": "application",
            "equals": {
                "path": "Application Number",
                "value": app_num
            }
        }
        }
    ])
    return result


def fuzzy_search_with_journal(tm_collection, query, journal, limit):
    result = tm_collection.aggregate([
        {"$search":
                {"index": "fuzzy",
                "compound": {
                    "should": [{
                        "text": {
                            "query": query,
                            "path": {
                                "wildcard": "*"
                            },
                            "fuzzy": {}
                        }
                    }],
                    "filter": [{
                        "equals": {
                            "path": "Journal Number",
                            "value": journal
                        }
                    }]
                }
                }
            },
        {
            "$limit": limit
        },
        {
            "$project": {
            "Application Number": 1,
            "TM Applied For": 1,
            "Class": 1,
            "Wordmark": 1,
            "score": { "$meta": "searchScore" }
            }
        }
    ])
    return result


def journal_conflict_search(journal_conflict_collection, organization, journal_number, min_risk, max_risk, class_category, app_num_list=None):
    filter_condition = [{
                      "equals": {
                          "path": "journal_number",
                          "value": journal_number
                      }
                  },
                      {
                      "in": {
                          "path": "class_category",
                          "value": class_category
                      }
                  },
                      {
                      "range": {
                          "path": "risk_level",
                          "gte": min_risk,
                          "lte": max_risk
                      }

                  }
    ]
    if app_num_list is not None:
        filter_condition.append({
                      "in": {
                          "path": "query_application_number",
                          "value": app_num_list
                      }
                  })
    meta = journal_conflict_collection.aggregate([
        {"$searchMeta":
             {"index": "journal-conflict-query",
              "compound": {
                  "must": [{
                      "text": {
                          "query": organization,
                          "path": "organization",
                      }
                  }],
                  "filter": filter_condition
              },
              "count": {
                  "type": "total"
              }
              },
         }
    ])
    return meta

