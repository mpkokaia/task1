# -*- coding: utf-8 -*-
import re
import math
from pymongo import Connection


class FisherClassifier():
    def __init__(self, db):
        self.features_count = {}
        self.category_count = {}
        self.minimums = {}
        self.db = db

    def getwords(self, doc):
        words = [s.lower() for s in re.findall(u'([А-Яа-яA-Za-z-0-9]+)', doc.lower()) if len(s) > 3 and len(s) < 20]
        return words

    def train(self, all_data, category):
        features = self.getwords(all_data)
        for f in features:
            self.inc_features(f, category)
        self.inc_category(category)

    def inc_features(self, features, category):
        if self.db.features_count.find_one({'features': features, 'category': category}):
            self.db.features_count.update({'features': features,
                                           'category': category}, {'$inc': {'count': 1}})
        else:
            self.db.features_count.save({'features': features,
                                         'category': category, 'count': 1})

    def inc_category(self, category):
        if self.db.category_count.find_one({'category': category}):
            self.db.category_count.save({'category': category, 'count': 1})
        else:
            self.db.category_count.update({'category': category}, {'$inc': {'count': 1}})


    def classify(self, all_words):
        best = None
        max = 0.0
        for category in self.categories():
            p = self.fisher_probability(all_words, category)
            get_min = 0
            if category in self.minimums:
                get_min = self.minimums[category]
            if p > get_min and p > max:
                best = category
                max = p
        return best

    def fcount(self, features, category):
        res = self.db.features_count.find_one({'features': features,
                                               'category': category}, {'count': 1, '_id': 0})
        if res:
            return float(res['count'])
        else:
            return 0

    def categories(self):
        data = []
        for r in self.db.category_count.find({}, {'category': 1, '_id': 0}):
            data.append(r['category'])
        return data


    def features_probability(self, features, category):
        category_count = 0
        res = self.db.category_count.find_one({'category': category}, {'count': 1, '_id': 0})
        if res:
            category_count = float(res['count'])
            return self.fcount(features, category) / category_count
        else:
            return 0


    def weighted_probability(self, features, category, weight=1.0, ap=0.5):
        prob = 0
        clf = self.features_probability(features, category)
        if clf != 0:
            freqsum = sum([self.features_probability(features, c) for c in self.categories()])
            p = clf / (freqsum)
            prob = p
        totals = sum([self.fcount(features, c) for c in self.categories()])
        bp = ((weight * ap) + (totals * prob)) / (weight + totals)
        return bp


    def fisher_probability(self, all_words, category):
        p = 1
        features = self.getwords(all_words)
        for f in features:
            p *= (self.weighted_probability(f, category))
        m = -2 * math.log(p) / 2.0
        count = term = math.exp(-m)
        for i in range(1, (len(features) * 2) / 2):
            term *= m / i
            count += term
        return min(count, 1.0)


def train(db):
    data = db.users.find({'users_get.universities.graduation': 2013},
                         {'vkid': 1, '_id': 0, 'users_get': 1})
    for user in data:
        if u'interests' in user['users_get']:
            all_data = user['users_get']['interests']
            if all_data:
                print all_data
                category = raw_input('1-good, 0-bad')
                if category == '1':
                    cat = 'good'
                elif category == '0':
                    cat = 'bad'
                cl = FisherClassifier(db)
                cl.train(all_data, cat)


def classify(db):
    data = db.users.find()
    for user in data:
        if u'interests' in user['users_get']:
            all_data = user['users_get']['interests']
            if all_data:
                cl = FisherClassifier(db)
                res = cl.classify(all_data)
                if res == 'bad':
                    db.bad_users.save({'vk_id': user['vkid']})
                    continue
        db.filter_users.save(user)


connection = Connection()
db = connection.urfu
#train(db)
classify(db)

