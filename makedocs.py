#!/usr/bin/env python

import argparse
import subprocess
import os.path
import shutil
import sys

DEFAULT_TAG = '0.1'
CLONE_URL = 'https://gitlab.cr.usgs.gov/mhearne/pager2.git'

def getCommandOutput(cmd):
    """
    Internal method for calling external command.
    @param cmd: String command ('ls -l', etc.)
    @return: Three-element tuple containing a boolean indicating success or failure, 
    the stdout from running the command, and stderr.
    """
    proc = subprocess.Popen(cmd,
                            shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE
                            )
    stdout, stderr = proc.communicate()
    retcode = proc.returncode
    stdout = stdout.decode('utf-8')
    if retcode == 0:
        retcode = True
    else:
        retcode = False
    return (retcode, stdout, stderr)


def main(args):
    # where should .rst files, Makefile, _build folder be written?
    SPHINX_DIR = os.path.join(os.path.expanduser('~'), '__api-doc')

    #where should the temporary clone of the pager gh-pages repo live?
    CLONE_DIR=os.path.join(os.path.expanduser('~'),'__pager-doc')

    # where is the repository where this script is running?
    REPO_DIR = os.path.dirname(os.path.abspath(__file__))  # where is this script?

    # get the human friendly version of the Pager version
    res, verstr, stderr = getCommandOutput('git describe')
    if not len(verstr.strip()):
        verstr = DEFAULT_TAG
    verstr = verstr.strip()
        
    # what is the package called and who are the authors
    PACKAGE = "pager"
    AUTHORS = 'Mike Hearne'

    # find the make command on this system
    res, stdout, stderr = getCommandOutput('which make')
    if not res:
        print('Could not find the "make" command on your system. Exiting.')
        sys.exit(1)
    make_cmd = stdout.strip()

    try:
        if args.post:
            #clone the repository
            sys.stderr.write('Cloning pager gh-pages branch...\n')
            if os.path.isdir(CLONE_DIR):
                shutil.rmtree(CLONE_DIR)
            clonecmd = 'git clone -b gh-pages %s %s' % (CLONE_URL,CLONE_DIR)
            res,stdout,stderr = getCommandOutput(clonecmd)
            if not res:
                raise Exception('Could not clone gh-pages branch.')

        #remove the current apidocs folder from that repo
        apidocfolder = os.path.join(CLONE_DIR,'apidoc') #this should probably not have 'html' in the path
        if os.path.isdir(apidocfolder):
            shutil.rmtree(apidocfolder)

        #run the sphinx api doc command
        sys.stderr.write('Building pager API documentation (REST)...\n')
        package_dir = os.path.join(REPO_DIR,'losspager')
        sphinx_cmd = 'sphinx-apidoc -o %s -f -l -F -H %s -A "%s" -V %s %s' % (SPHINX_DIR,PACKAGE,AUTHORS,verstr,package_dir)
        res,stdout,stderr = getCommandOutput(sphinx_cmd)
        if not res:
            raise Exception('Could not build Pager API documentation - error "%s".' % stderr)

        #this has created a conf.py file and a Makefile.  We need to "edit" the conf.py file to include the ReadTheDocs theme.
        fname = os.path.join(SPHINX_DIR,'conf.py')
        f = open(fname,'at')
        f.write("sys.path.insert(0, os.path.abspath('%s'))\n" % (REPO_DIR))
        f.write("import sphinx_rtd_theme\n")
        f.write("html_theme = 'sphinx_rtd_theme'\n")
        f.write("html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]\n")
        f.write("autoclass_content = 'both'\n")
        f.close()

        #Go to the sphinx directory and build the html
        sys.stderr.write('Building pager API documentation (HTML)...\n')
        os.chdir(SPHINX_DIR)
        res,stdout,stderr = getCommandOutput('%s html' % make_cmd)
        if not res:
            raise Exception('Could not build HTML for API documentation. - error "%s"' % stderr)

        if args.post:
            #copy the generated content to the gh-pages branch we created earlier
            htmldir = os.path.join(SPHINX_DIR,'_build','html')
            if os.path.isdir(apidocfolder):
                shutil.rmtree(apidocfolder)
            shutil.copytree(htmldir, apidocfolder)
            
            #cd to directory above where html content was pushed
            htmldir = os.path.join(CLONE_DIR) #this should probably not have 'html' in it
            os.chdir(htmldir)
            res,stdout,stderr = getCommandOutput('touch .nojekyll')
            res1,stdout,stderr1 = getCommandOutput('git add --all')
            res2,stdout,stderr2 = getCommandOutput('git commit -am"Pushing version %s to GitHub pages"' % verstr)
            res3,stdout,stderr3 = getCommandOutput('git push -u origin +gh-pages')
            if res1+res2+res3 < 3:
                stderr = stderr1+stderr2+stderr3
                print('Something bad happened when attempting to add, commit, or push gh-pages content to GitHub - error "%s". Exiting.' % stderr)
                sys.exit(1)
            print('You can inspect the Pager manual and API docs by looking here: http://usgs.github.io/pager/index.html')
        else:
            if not args.clean:
                indexpage = os.path.join(SPHINX_DIR,'_build','html','index.html') #this should not have 'html' in it
                print('You can inspect the Pager manual and API docs by looking here: %s' % indexpage)
    except Exception as error:
        print('Error detected: %s' % str(error))
    finally:
        if args.clean:
            print('Cleaning up %s created directory...' % (SPHINX_DIR))
            shutil.rmtree(SPHINX_DIR)
            if args.post:            
                print('Cleaning up %s created directory...' % (CLONE_DIR))
                shutil.rmtree(CLONE_DIR)
            


if __name__ == '__main__':
    desc = '''Create API documentation for Pager and optionally post HTML output to GitHub.
    '''
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('-p', '--post', action='store_true', default=False,
                        help='Post content to the web')
    parser.add_argument('-c', '--clean', action='store_true', default=False,
                        help='Clean up local directories containing generated HTML content')

    pargs = parser.parse_args()
    main(pargs)
