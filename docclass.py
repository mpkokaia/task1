# -*- coding: utf-8 -*-
import re
import math
from pymongo import Connection
import webbrowser

def getwords(doc):
    words=[s.lower() for s in re.findall(u'([А-Яа-яA-Za-z-0-9]+)', doc.lower()) if len(s)>3 and len(s)<20]
    return dict([(w,1) for w in words])     

class classifier:
    def __init__(self,getfeatures,filename=None):
        self.features_count={}
        self.category_count={}
        self.getfeatures=getfeatures

    def setdb(self):
        connection = Connection()
        self.db = connection.fisher
    
    def incf(self,features,category):
        count=self.fcount(features,category)
        if count==0:
            self.db.features_count.save({'features':features,'category': category,'count':1 }) 
        else:
            self.db.features_count.update({'features':features,'category': category},{ '$inc' : { 'count' : 1 } })

    def incc(self,category): 
        count=self.catcount(category)
        if count==0:
            self.db.category_count.save({'category': category,'count':1 }) 
        else:
            self.db.category_count.update({'category': category},{ '$inc' : { 'count' : 1 } })

    def fcount(self,features,category):
        res=self.db.features_count.find({'features':features,'category': category},{'count':1,'_id':0})
        data=[]
        for r in res:
            data.append(r)
        if data: return float(data[0]['count'])
        else: return 0

    def catcount(self,category):
        res=self.db.category_count.find({'category': category},{'count':1,'_id':0})
        data=[]
        for r in res:
            data.append(r)

        if data: return float(data[0]['count'])
        else: return 0

    def totalcount(self):
        res=self.db.category_count.find({},{'count':1,'_id':0})
        data=[]
        for r in res:
            data.append(r['count'])
        if data: return sum(data)
        else: return 0

 
    def categories(self):
        cur=self.db.category_count.find({},{'category':1,'_id':0})
        data=[]
        for r in cur:
            data.append(r['category'])
        return data

    def train(self,item,category):
        features=self.getfeatures(item)
        for f in features:
          self.incf(f,category)
        self.incc(category)
    def fprob(self,features,category):
        if self.catcount(category)==0:
            return 0
        return self.fcount(features,category)/self.catcount(category)

    def weightedprob(self, features, category, prf, weight=1.0,  ap=0.5):
        basicprob = prf(features, category)

        totals = sum([self.fcount(features, c) for c in self.categories()])
        bp = ((weight*ap)+(totals*basicprob))/(weight+totals)
        return bp


class fisherclassifier(classifier):
    def cprob(self, f, cat):
        clf = self.fprob(f, cat)
        if clf == 0: return 0
        freqsum = sum([self.fprob(f, c) for c in self.categories()])
        p = clf/(freqsum)

        return p
    def fisherprob(self,  item, cat):
        p=1
        features = self.getfeatures(item)
        for f in features:
            p*=(self.weightedprob(f, cat, self.cprob))

        fscore = -2*math.log(p)
        return self.invchi2(fscore,  len(features)*2)

    def invchi2(self, chi,  df):
        m = chi / 2.0
        sum = term = math.exp(-m)
        for i in range(1, df//2):
            term *= m / i
            sum += term
        return min(sum, 1.0)

    def __init__(self, getfeatures):
        classifier.__init__(self, getfeatures)
        self.minimums = {}

    def setminimum(self,  cat,  min):
        self.minimums[cat] = min

    def getminimum(self,  cat):
        if cat not in self.minimums:
            return 0
        return self.minimums[cat]
    def classify(self,  item,  default=None):
        best = default
        max = 0.0
        for c in self.categories():
            p = self.fisherprob(item,  c)
            if p > self.getminimum(c) and p > max:
                best = c
                max = p
        return best
def train():
    connection = Connection()
    db = connection.urfu   
    data=db.users.find({'users_get.universities.graduation':2013},{'vkid':1,'_id':0,'wall_get':1,'users_get':1})
    all_data=''
    for user in data:
        url = 'https://vk.com/'+str(user['users_get']['domain'])
        webbrowser.open(url)
        for i in range(1,len(user['wall_get'])):
            if  u'text' in user['wall_get'][i]:
                all_data+=user['wall_get'][i]['text']+' '
        if  u'interests' in user['users_get']:
            all_data+=user['users_get']['interests']+' '
        category=raw_input('1-good, 0-bad')
        if category=='1':
            cat='good'
        elif category=='0':
            cat='bad'
        cl=fisherclassifier(getwords)
        cl.setdb()
        cl.train(all_data,cat)
        all_data=''
train()

