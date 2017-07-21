import os
import json

from slackclient import SlackClient


slack_test_token = os.environ["SLACK_BOT_TOKEN"]
sc = SlackClient(slack_test_token)

link_msglst_dict = {}
uid_to_nidx = {}
uid_to_name = {}

users_ret = sc.api_call("users.list")
if not users_ret['ok']:
    print "cannot retrieve users list, exiting..."

jsonfile = open(r'inputData.json', 'w')
jsonfile.write('{\n')
jsonfile.write('    "nodes":[\n')

users = users_ret['members']
i = 0
for user in users:
    uid_to_name[user['id']] = user['real_name']
    uid_to_nidx[user['id']] = i
    email = user['profile']['email'] if 'email' in user['profile'] else ''
    if user['real_name'] != 'slackbot' and user['real_name'] and email:
        if i > 0:
            jsonfile.write('        },\n')
        jsonfile.write('        {\n')
        jsonfile.write('            "id":"' + user['id'] + '",\n')
        namestrs = user['real_name'].split(' ')
        simp_name_str = ''
        for idx in range(len(namestrs)-1):
            simp_name_str += namestrs[idx][0] + '. '
        simp_name_str += namestrs[-1]
        jsonfile.write('            "name":"' + simp_name_str + '",\n')
        jsonfile.write('            "color":"' + user['color'] + '",\n')
        jsonfile.write('            "email":"' + email + '"\n')
        i += 1

jsonfile.write('        }\n')
jsonfile.write('    ],\n')

channels_ret = sc.api_call("channels.list")
if not channels_ret['ok']:
    print "cannot retrieve channels list, exiting..."

for channel in channels_ret['channels']:
    ch_name = channel['name']

    channel_hist_ret = sc.api_call("channels.history",
                                   channel=channel['id'],
                                   inclusive=True)
    if not channel_hist_ret['ok']:
        print "cannot retrieve channels history, exiting..."
    msgs = channel_hist_ret['messages']
    more = channel_hist_ret['has_more']
    for msg in msgs:
        if not 'user' in msg:
            continue
        if 'reactions' in msg:
            source = uid_to_nidx[msg['user']]
            if 'text' in msg:
                txtstr = msg['text']
            else:
                txtstr = ''
            for react in msg['reactions']:
                for ru in react['users']:
                    target = uid_to_nidx[ru]
                    key_str = str(source) + '-' + str(target)
                    if key_str in link_msglst_dict:
                        link_msglst_dict[key_str]['count'] += 1
                        if ch_name not in link_msglst_dict[key_str]['channel']:
                            link_msglst_dict[key_str]['channel'] += ';' + ch_name
                        if txtstr:
                            if link_msglst_dict[key_str]['text']:
                                link_msglst_dict[key_str]['text'] += '\n:' + txtstr
                            else:
                                link_msglst_dict[key_str]['text'] = txtstr
                    else:
                        link_msglst_dict[key_str] = {'channel': ch_name,
                                                     'text': txtstr,
                                                     'count': 1}

    while more:
        last_ts = msgs[-1]['ts']
        channel_hist_ret = sc.api_call("channels.history",
                                       channel=channel['id'],
                                       latest=last_ts)
        if not channel_hist_ret['ok']:
            print "cannot retrieve channels history, exiting..."

        msgs = channel_hist_ret['messages']
        for msg in msgs:
            if not 'user' in msg:
                continue
            if 'reactions' in msg:
                source = uid_to_nidx[msg['user']]
                if 'text' in msg:
                    txtstr = msg['text']
                else:
                    txtstr = ''
                for react in msg['reactions']:
                    for ru in react['users']:
                        target = uid_to_nidx[ru]
                        key_str = str(source) + '-' + str(target)
                        if key_str in link_msglst_dict:
                            link_msglst_dict[key_str]['count'] += 1
                            if ch_name not in link_msglst_dict[key_str]['channel']:
                                link_msglst_dict[key_str]['channel'] += ';' + ch_name
                            if txtstr:
                                link_msglst_dict[key_str]['text'] += ';' + txtstr
                        else:
                            link_msglst_dict[key_str] = {'channel': ch_name,
                                                         'text': txtstr,
                                                         'count': 1}

        more = channel_hist_ret['has_more']

jsonfile.write('    "links":[\n')
i = 0

for key, msg_dict in link_msglst_dict.items():
    if i > 0:
        jsonfile.write('        },\n')
    jsonfile.write('        {\n')
    split_keys = key.split('-')
    source = split_keys[0]
    target = split_keys[1]
    jsonfile.write('            "source": ' + source + ',\n')
    jsonfile.write('            "target": ' + target + ',\n')
    jsonfile.write('            "channel":"' + msg_dict['channel'] + '",\n')
    if msg_dict['text'].find(u'\u2019') >= 0:
        msg_dict['text'] = msg_dict['text'].replace(u'\u2019', '\'')
    if msg_dict['text'].find('\n') >= 0:
        msg_dict['text'] = msg_dict['text'].replace('\n', '...')
    jsonfile.write('            "text":"' + msg_dict['text'] + '",\n')
    jsonfile.write('            "count":' + str(msg_dict['count']) + '\n')
    i += 1

jsonfile.write('        }\n')
jsonfile.write('    ]\n')
jsonfile.write('}')
