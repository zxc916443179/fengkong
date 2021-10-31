import ConfigParser
import codecs

cp = ConfigParser.SafeConfigParser()
with codecs.open("settings.conf", 'r', encoding="gb2312") as f:
    cp.readfp(f)

print(cp.get('server', 'ip'))

