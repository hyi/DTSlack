import os
import json
import unicodedata

from slackclient import SlackClient

link_msglst_dict = {}


def create_links_from_messages(sc, msgs, ch_id, ch_name):
    for msg in msgs:
        if not 'user' in msg:
            continue

        source = msg['user']
        stxtstr = msg['text'] if 'text' in msg else ''

        type = ''

        if 'reactions' in msg:
            type = 'reaction'
            for react in msg['reactions']:
                for ru in react['users']:
                    target = ru
                    key_str = str(source) + '-' + str(target) + '-' + msg['ts'] + '-' + type
                    if key_str in link_msglst_dict:
                        link_msglst_dict[key_str]['count'] += 1
                        if ch_name not in link_msglst_dict[key_str]['channel']:
                            link_msglst_dict[key_str]['channel'] += ';' + ch_name
                        if link_msglst_dict[key_str]['reactions']:
                            link_msglst_dict[key_str]['reactions'] += ':' + react['name']
                    else:
                        link_msglst_dict[key_str] = {'type': type,
                                                     'channel': ch_name,
                                                     'text': stxtstr,
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
                        key_str = str(source) + '-' + str(target) + '-' + msg['ts'] + '-' + type
                        if key_str in link_msglst_dict:
                            link_msglst_dict[key_str]['count'] += 1
                            if ch_name not in link_msglst_dict[key_str]['channel']:
                                link_msglst_dict[key_str]['channel'] += ';' + ch_name
                            if 'text' in rmsg:
                                html_msg_str = '<li>' + rmsg['text'] + '</li>'
                                link_msglst_dict[key_str]['threaded_text'] += html_msg_str
                        else:
                            html_msg_str = '<ul><li>' + rmsg['text'] + '</li>' if 'text' in rmsg \
                                else ''
                            link_msglst_dict[key_str] = {'type': type,
                                                         'channel': ch_name,
                                                         'text': stxtstr,
                                                         'threaded_text': html_msg_str,
                                                         'count': 1}

        if not type:
            txt = msg['text']
            idx2 = 0
            while '@' in txt:
                idx1 = txt.find('@', idx2)
                idx2 = txt.find('|', idx1)
                if idx2 == -1:
                    idx2 = txt.find('>', idx1)
                if source != txt[idx1+1:idx2]:
                    if txt[idx1+1:idx2] in uid_to_node:
                        # can create message link here
                        print uid_to_node[source]['name'] + '-' + uid_to_node[txt[idx1+1:idx2]]['name'] + '-' + txt
                if idx2 == -1 or idx2 >= len(txt)-1:
                    # end of the text string, break the while loop
                    break

# append </ul> to all threaded_text key in link_msglist_dict
def append_list_end_to_all_msgs():
    for key, val_dict in link_msglst_dict.iteritems():
        if 'threaded_text' in val_dict:
            if '<ul>' in val_dict['threaded_text'] and '</ul>' not in val_dict['threaded_text']:
                val_dict['threaded_text'] += '</ul>'


# fetch threaded message interactions from channels.history
def getInteractionMessages(sc):
    channels_ret = sc.api_call("channels.list")
    if not channels_ret['ok']:
        print "cannot retrieve channels list, exiting..."

    for channel in channels_ret['channels']:
        channel_hist_ret = sc.api_call("channels.history",
                                       channel=channel['id'],
                                       inclusive=True)
        if not channel_hist_ret['ok']:
            print "cannot retrieve channels history, exiting..."
        msgs = channel_hist_ret['messages']
        more = channel_hist_ret['has_more']

        create_links_from_messages(sc, msgs, channel['id'], channel['name'])

        while more:
            last_ts = msgs[-1]['ts']
            channel_hist_ret = sc.api_call("channels.history",
                                           channel=channel['id'],
                                           latest=last_ts)
            if not channel_hist_ret['ok']:
                print "cannot retrieve channels history, exiting..."

            msgs = channel_hist_ret['messages']
            create_links_from_messages(sc, msgs, channel['id'], channel['name'])
            more = channel_hist_ret['has_more']

        append_list_end_to_all_msgs()

def convert_unicode_to_ascii(ustr):
    if ustr.find(u'\u2019') >= 0:
        ustr = ustr.replace(u'\u2019', '\'')
    if ustr.find('\n') >= 0:
        ustr = ustr.replace('\n', '...')

    return ustr.encode('ascii', 'ignore')


if __name__ == "__main__":
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
            simp_name_str = ''
            for idx in range(len(namestrs)-1):
                simp_name_str += namestrs[idx][0] + '. '
            simp_name_str += namestrs[-1]
            node_dict['name'] = simp_name_str
            node_dict['color'] = user['color']
            node_dict['email'] = email
            uid_to_node[user['id']] = node_dict

    getInteractionMessages(sc)

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
