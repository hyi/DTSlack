import re
import os
import json
import csv
import cgi
import unicodedata
import numpy as np

from slackclient import SlackClient
from sklearn.feature_extraction.text import CountVectorizer

link_msglst_dict = {}
name_color = {}


def create_links_from_messages(sc, msgs, ch_id, ch_name, mtext):
    msg_text = mtext
    for msg in msgs:
        if not 'user' in msg:
            continue

        source = msg['user']
        stxtstr = cgi.escape(msg['text']) if 'text' in msg else ''
        if msg_text:
            msg_text = msg_text + ' ' + msg['text']
        else:
            msg_text = msg['text']
            
        type = ''

        if 'reactions' in msg:
            type = 'reaction'
            for react in msg['reactions']:
                for ru in react['users']:
                    target = ru
                    key_str = str(source) + '-' + str(target) + '-' + msg['ts'] + '-' + type
                    if key_str in link_msglst_dict:
                        link_msglst_dict[key_str]['count'] += 1
                        if stxtstr and stxtstr not in link_msglst_dict[key_str]['text']:
                            link_msglst_dict[key_str]['text'] += '<li>' + stxtstr + '</li>'
                        if ch_name not in link_msglst_dict[key_str]['channel']:
                            link_msglst_dict[key_str]['channel'] += ';' + ch_name
                        if link_msglst_dict[key_str]['reactions']:
                            link_msglst_dict[key_str]['reactions'] += ';' + react['name']
                    else:
                        link_msglst_dict[key_str] = {'type': type,
                                                     'channel': ch_name,
                                                     'text': '<ul><li>' + stxtstr + '</li>',
                                                     'reactions': react['name'],
                                                     'count': 1}

        if 'thread_ts' in msg:
            type = 'thread'
            if msg['ts'] == msg['thread_ts']:
                channel_reply_ret = sc.api_call("channels.replies",
                                                channel=ch_id,
                                                thread_ts=msg['thread_ts'])
                if not channel_reply_ret['ok']:
                    print "cannot retrieve channel replies for parent " + msg['thread_ts'] + ", exiting..."

                rmsgs = channel_reply_ret['messages']
                for rmsg in rmsgs:
                    target = rmsg['user']
                    if source != target:
                        ttxtstr = cgi.escape(rmsg['text']) if 'text' in rmsg \
                                else ''
                        if ttxtstr:
                            msg_text += ' ' + rmsg['text']
                        key_str = str(source) + '-' + str(target) + '-' + msg['ts'] + '-' + type
                        if key_str in link_msglst_dict:
                            link_msglst_dict[key_str]['count'] += 1
                            if stxtstr and stxtstr not in link_msglst_dict[key_str]['text']:
                                link_msglst_dict[key_str]['text'] += '<li>' + stxtstr + '</li>'
                            if ch_name not in link_msglst_dict[key_str]['channel']:
                                link_msglst_dict[key_str]['channel'] += ';' + ch_name
                            if ttxtstr:
                                html_msg_str = '<li>' + ttxtstr + '</li>'
                                link_msglst_dict[key_str]['threaded_text'] += html_msg_str
                        else:
                            html_msg_str = '<ul><li>' + ttxtstr + '</li>' if ttxtstr else ''
                            link_msglst_dict[key_str] = {'type': type,
                                                         'channel': ch_name,
                                                         'text': '<ul><li>' + stxtstr + '</li>',
                                                         'threaded_text': html_msg_str,
                                                         'count': 1}

        if not type:
            txt = msg['text']
            if '@' in txt:
                type = 'at'
            else:
                type = 'broadcast'
            idx2 = 0
            while '@' in txt:
                idx1 = txt.find('@', idx2)
                if idx1 == -1:
                    break
                idx2 = txt.find('|', idx1)
                if idx2 == -1:
                    idx2 = txt.find('>', idx1)
                if idx2 == -1 or idx2 >= len(txt)-1:
                    # end of the text string, break the while loop
                    break
                if source != txt[idx1+1:idx2]:
                    if txt[idx1+1:idx2] in uid_to_node:
                        # create message link here
                        target = txt[idx1+1:idx2]
                        key_str = str(source) + '-' + str(target) + '-' + msg['ts'] + '-' + type
                        txt = txt.replace(target, uid_to_node[target]['name'])
                        escape_txt = cgi.escape(txt)
                        if key_str in link_msglst_dict:
                            link_msglst_dict[key_str]['count'] += 1
                            if ch_name not in link_msglst_dict[key_str]['channel']:
                                link_msglst_dict[key_str]['channel'] += ';' + ch_name
                            html_msg_str = '<li>' + escape_txt + '</li>'
                            if html_msg_str not in link_msglst_dict[key_str]['text']:
                                link_msglst_dict[key_str]['text'] += html_msg_str
                        else:
                            html_msg_str = '<ul><li>' + escape_txt + '</li>'
                            link_msglst_dict[key_str] = {'type': type,
                                                         'channel': ch_name,
                                                         'text': html_msg_str,
                                                         'count': 1}

            if type == 'broadcast':
                # add broadcast msg to the corresponding user node
                escape_txt = cgi.escape(txt)
                if uid_to_node[source]['broadcast_messages']:
                    html_msg_str = '<li>' + escape_txt + '</li>'
                else:
                    html_msg_str = '<ul><li>' + escape_txt + '</li>'

                if html_msg_str not in uid_to_node[source]['broadcast_messages'] and \
                                uid_to_node[source]['broadcast_msg_count'] < 5:
                    uid_to_node[source]['broadcast_messages'] += html_msg_str

                uid_to_node[source]['broadcast_msg_count'] += 1
    return msg_text
    
    
# append </ul> to all threaded_text key in link_msglist_dict
def append_list_end_to_all_msgs():
    for key, val_dict in link_msglst_dict.iteritems():
        if 'threaded_text' in val_dict:
            if '<ul>' in val_dict['threaded_text'] and '</ul>' not in val_dict['threaded_text']:
                val_dict['threaded_text'] += '</ul>'
        if 'text' in val_dict:
            if '<ul>' in val_dict['text'] and '</ul>' not in val_dict['text']:
                val_dict['text'] += '</ul>'

    for uid, val_dict in uid_to_node.iteritems():
        if '<ul>' in val_dict['broadcast_messages'] and '</ul>' not in val_dict['broadcast_messages']:
            val_dict['broadcast_messages'] += '</ul>'


# fetch threaded message interactions from channels.history
def getInteractionMessages(sc):
    channels_ret = sc.api_call("channels.list")
    if not channels_ret['ok']:
        print "cannot retrieve channels list, exiting..."
    msg_text = ''    
    for channel in channels_ret['channels']:
        channel_hist_ret = sc.api_call("channels.history",
                                       channel=channel['id'],
                                       inclusive=True)
        if not channel_hist_ret['ok']:
            print "cannot retrieve channels history, exiting..."
        msgs = channel_hist_ret['messages']
        more = channel_hist_ret['has_more']
        
        msg_text = create_links_from_messages(sc, msgs, channel['id'], channel['name'], msg_text)

        while more:
            last_ts = msgs[-1]['ts']
            channel_hist_ret = sc.api_call("channels.history",
                                           channel=channel['id'],
                                           latest=last_ts)
            if not channel_hist_ret['ok']:
                print "cannot retrieve channels history, exiting..."

            msgs = channel_hist_ret['messages']
            msg_text = create_links_from_messages(sc, msgs, channel['id'], channel['name'], msg_text)
            more = channel_hist_ret['has_more']

    append_list_end_to_all_msgs()
    return msg_text


def convert_unicode_to_ascii(ustr):
    if not ustr:
        return ''

    if ustr.find(u'\u2019') >= 0:
        ustr = ustr.replace(u'\u2019', '\'')
    if ustr.find(u'\u2026') >= 0:
        ustr = ustr.replace(u'\u2026', '.')
    if ustr.find('\n') >= 0:
        ustr = ustr.replace('\n', '. ')
    # replace double quotes with single quotes since double quotes are used in JSON file
    if ustr.find('"') >= 0:
        ustr = ustr.replace('"', "'")
    if ustr.find(u'\u201c') >= 0:
        ustr = ustr.replace(u'\u201c', "'")
    if ustr.find(u'\u201d') >= 0:
        ustr = ustr.replace(u'\u201d', "'")
    if ustr.find(u'\u2014') >= 0:
        ustr = ustr.replace(u'\u2014', '-')
    if ustr.find(u'\u2013') >= 0:
        ustr = ustr.replace(u'\u2013', '-')
    if ustr.find(u'\u2018') >= 0:
        ustr = ustr.replace(u'\u2018', '_')
    OnlyAscii = lambda s: re.match('^[\x00-\x7F]+$', s) != None
    if not OnlyAscii(ustr):
        ustr = ustr.encode('ascii')
    if ustr.find(u'\u0009') >= 0:
        ustr = ustr.replace(u'\u0009', ' ')
    return ustr


def generate_word_cloud(mtxt):
    cv = CountVectorizer()
    cv = CountVectorizer(min_df=0, decode_error="ignore",                                               
                         stop_words="english", max_features=200)
    counts = cv.fit_transform([mtxt]).toarray().ravel()                                                  
    words = cv.get_feature_names() 
    # normalize                                                                                                                                             
    counts = counts / float(counts.max())
    print "text = " + mtxt
    print counts
    print words
    with open('wordCloud.json', 'w') as fp:
        fp.write('{\n')
        fp.write('    "words":[\n')
        for i in range(len(words)):
            if i > 0:
                fp.write('        },\n')
            fp.write('        {\n')
            fp.write('            "text":"' + words[i] + '",\n')
            fp.write('            "size":' + str(counts[i]) + '\n')
        fp.write('        }\n')
        fp.write('    ]\n')    
        fp.write('}')                        

    
if __name__ == "__main__":
    # read team name to color mapping csv file
    with open('DTTeamNameColorMapping.csv', 'r') as fp:
        csv_data = csv.reader(fp)
        for row in csv_data:
            split_name_str = row[0].split()
            if len(split_name_str) == 1:
                name = split_name_str[0]
            else:
                name = split_name_str[0][0] + '. ' + split_name_str[-1]
            clr = row[1]
            name_color[name.lower()] = clr.lower()

    slack_test_token = os.environ["SLACK_BOT_TOKEN"]
    sc = SlackClient(slack_test_token)

    uid_to_node = {}
    uid_to_nidx = {}

    users_ret = sc.api_call("users.list")
    if not users_ret['ok']:
        print "cannot retrieve users list, exiting..."

    users = users_ret['members']
    for user in users:
        email = user['profile']['email'] if 'email' in user['profile'] else ''
        if user['real_name'] != 'slackbot' and user['real_name'] and email:
            node_dict = {}
            namestrs = user['real_name'].split(' ')
            if len(namestrs) == 1:
                simp_name_str = namestrs[0]
            else:
                simp_name_str = namestrs[0][0] + '. ' + namestrs[-1]

            node_dict['real_name'] = user['real_name']
            node_dict['name'] = simp_name_str
            node_dict['color'] = user['color']
            node_dict['email'] = email
            node_dict['broadcast_messages'] = ''
            node_dict['broadcast_msg_count'] = 0
            uid_to_node[user['id']] = node_dict

    msg_text = getInteractionMessages(sc)

    jsonfile = open(r'inputData.json', 'w')
    jsonfile.write('{\n')
    jsonfile.write('    "nodes":[\n')

    # write nodes
    i = 0
    for k, node_dict in uid_to_node.iteritems():
        name = node_dict['name']
        # color = node_dict['color']
        key = name.lower()
        if key in name_color:
            color = name_color[name.lower()]
        else:
            color = 'yellow'
            print node_dict['real_name']

        email = node_dict['email']
        uid_to_nidx[k] = i
        if i > 0:
            jsonfile.write('        },\n')
        jsonfile.write('        {\n')
        jsonfile.write('            "id":"' + k + '",\n')
        jsonfile.write('            "name":"' + node_dict['name'] + '",\n')
        jsonfile.write('            "color":"' + color + '",\n')
        jsonfile.write('            "email":"' + node_dict['email'] + '",\n')
        jsonfile.write('            "broadcast_msg_count":' + str(node_dict['broadcast_msg_count']) + ',\n')
        msgstr = convert_unicode_to_ascii(node_dict['broadcast_messages'])
        #if i != 85:
        #    jsonfile.write('            "broadcast_messages":"' + msgstr + '"\n')
        #else:
        #    jsonfile.write('            "broadcast_messages":"' + '"\n')
        jsonfile.write('            "broadcast_messages":"' + msgstr + '"\n')
        i += 1

    jsonfile.write('        }\n')
    jsonfile.write('    ],\n')

    # write links
    jsonfile.write('    "links":[\n')
    i = 0
    for key, msg_dict in link_msglst_dict.iteritems():
        if i > 0:
            jsonfile.write('        },\n')
        jsonfile.write('        {\n')
        split_keys = key.split('-')
        source = uid_to_nidx[split_keys[0]]
        target = uid_to_nidx[split_keys[1]]
        jsonfile.write('            "source": ' + str(source) + ',\n')
        jsonfile.write('            "target": ' + str(target) + ',\n')
        jsonfile.write('            "type":"' + msg_dict['type'] + '",\n')
        jsonfile.write('            "channel":"' + msg_dict['channel'] + '",\n')
        # convert unicode message str to ascii in order for js d3 to handle message display correctly
        thtxtstr = convert_unicode_to_ascii(msg_dict['text'])
        jsonfile.write('            "text":"' + thtxtstr + '",\n')
        if 'threaded_text' in msg_dict:
            thtxtstr = convert_unicode_to_ascii(msg_dict['threaded_text'])
            jsonfile.write('            "threaded_text":"' + thtxtstr + '",\n')
        if 'reactions' in msg_dict:
            thtxtstr = convert_unicode_to_ascii(msg_dict['reactions'])
            jsonfile.write('            "reactions":"' + thtxtstr + '",\n')

        jsonfile.write('            "count":' + str(msg_dict['count']) + '\n')
        i += 1

    jsonfile.write('        }\n')
    jsonfile.write('    ]\n')
    jsonfile.write('}')
    
    generate_word_cloud(msg_text)
    