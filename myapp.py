import os
import json

from slackclient import SlackClient


slack_test_token = os.environ["SLACK_BOT_TOKEN"]
sc = SlackClient(slack_test_token)

link_msglst_dict = {}
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
        simp_name_str = ''
        for idx in range(len(namestrs)-1):
            simp_name_str += namestrs[idx][0] + '. '
        simp_name_str += namestrs[-1]
        node_dict['name'] = simp_name_str
        node_dict['color'] = user['color']
        node_dict['email'] = email
        uid_to_node[user['id']] = node_dict

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
            source = msg['user']
            if 'text' in msg:
                txtstr = msg['text']
            else:
                txtstr = ''
            for react in msg['reactions']:
                for ru in react['users']:
                    target = ru
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
                source = msg['user']
                if 'text' in msg:
                    txtstr = msg['text']
                else:
                    txtstr = ''
                for react in msg['reactions']:
                    for ru in react['users']:
                        target = ru
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

jsonfile = open(r'inputData.json', 'w')
jsonfile.write('{\n')
jsonfile.write('    "nodes":[\n')

# write nodes
i = 0
for k, node_dict in uid_to_node.iteritems():
    name = node_dict['name']
    color = node_dict['color']
    email = node_dict['email']
    uid_to_nidx[k] = i
    if i > 0:
        jsonfile.write('        },\n')
    jsonfile.write('        {\n')
    jsonfile.write('            "id":"' + k + '",\n')
    jsonfile.write('            "name":"' + node_dict['name'] + '",\n')
    jsonfile.write('            "color":"' + node_dict['color'] + '",\n')
    jsonfile.write('            "email":"' + node_dict['email'] + '"\n')
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
