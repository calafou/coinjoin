import os
from pbxcore.config import config


def print_template(name, variables):
    f = open(os.path.join(config['root'], "templates", name + '.html'))
    data = f.read()
    f.close()
    return print_template_raw(data, variables)

def print_template_raw(data, variables):
    for var in variables:
        tpl_name = "%%" + var + "%%"
        if tpl_name in data:
            data = data.replace(tpl_name, str(variables[var]))
    return data


if __name__ == '__main__':
    print print_template('test', {'LINKS': '<li>foo</li>'})
