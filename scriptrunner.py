# DockerToolFactory.py
# see https://github.com/mvdbeek/scriptrunner

from __future__ import print_function
import sys
import shutil
import subprocess
import os
import time
import tempfile
import argparse
import math
from os.path import abspath

progname = os.path.split(sys.argv[0])[1]
verbose = False
debug = False

html_escape_table = {
    "&": "&amp;",
    ">": "&gt;",
    "<": "&lt;",
    "$": "\$"
}


def timenow():
    """Return current time as a string."""
    return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(time.time()))


def html_escape(text):
    """Produce entities within text."""
    return "".join(html_escape_table.get(c, c) for c in text)


def cmd_exists(cmd):
    return subprocess.call("type " + cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) == 0


def construct_bind(host_path, container_path=False, binds=None, ro=True):
    # TODO remove container_path if it's alwyas going to be the same as host_path
    """Build or extend binds dictionary with container path. binds is used
    to mount all files using the docker-py client."""
    if not binds:
        binds = {}
    if isinstance(host_path, list):
        for k, v in enumerate(host_path):
            if not container_path:
                container_path = host_path[k]
            binds[host_path[k]] = {'bind': container_path, 'ro': ro}
            container_path = False  # could be more elegant
        return binds
    else:
        if not container_path:
            container_path = host_path
        binds[host_path] = {'bind': container_path, 'ro': ro}
        return binds


def switch_to_docker(opts):
    import docker  # need local import, as container does not have docker-py
    user_id = os.getuid()
    group_id = os.getgid()
    docker_client = docker.APIClient()
    toolfactory_path = abspath(sys.argv[0])
    binds = construct_bind(host_path=opts.script_path, ro=False)
    binds = construct_bind(binds=binds, host_path=abspath(opts.output_dir), ro=False)
    if len(opts.input_file) > 0:
        binds = construct_bind(binds=binds, host_path=opts.input_file, ro=True)
    if not opts.output_file == 'None':
        binds = construct_bind(binds=binds, host_path=opts.output_file, ro=False)
    if opts.make_HTML:
        binds = construct_bind(binds=binds, host_path=opts.output_html, ro=False)
    binds = construct_bind(binds=binds, host_path=toolfactory_path)
    volumes = list(binds.keys())
    sys.argv = [abspath(opts.output_dir) if sys.argv[i - 1] == '--output_dir' else arg for i, arg in enumerate(sys.argv)]  # inject absolute path of working_dir
    cmd = ['python', '-u'] + sys.argv + ['--dockerized', '1', "--user_id", str(user_id), "--group_id", str(group_id)]
    image_exists = [True for image in docker_client.images() if opts.docker_image in image['RepoTags']]
    if not image_exists:
        docker_client.pull(opts.docker_image)
    container = docker_client.create_container(
        image=opts.docker_image,
        volumes=volumes,
        command=cmd,
        host_config=docker_client.create_host_config(binds=binds))
    docker_client.start(container=container[u'Id'])
    exit_code = docker_client.wait(container=container[u'Id'])['StatusCode']
    logs = docker_client.logs(container=container[u'Id'])
    print(logs, end="", file=sys.stderr)
    docker_client.remove_container(container[u'Id'])
    return exit_code


class ScriptRunner:
    """class is a wrapper for an arbitrary script
    """

    def __init__(self, opts=None, treatbashSpecial=True, image_tag='base'):
        """
        cleanup inputs, setup some outputs
        """
        self.opts = opts
        self.scriptname = 'script'
        self.temp_warned = False  # we want only one warning if $TMP not set
        self.treatbashSpecial = treatbashSpecial
        self.image_tag = image_tag
        os.chdir(abspath(opts.output_dir))
        self.thumbformat = 'png'
        s = open(self.opts.script_path, 'r').readlines()
        s = [x.rstrip() for x in s]  # remove pesky dos line endings if needed
        self.script = '\n'.join(s)
        fhandle, self.sfile = tempfile.mkstemp(prefix='script', suffix=".%s" % (opts.interpreter))
        tscript = open(self.sfile, 'w')  # use self.sfile as script source for Popen
        tscript.write(self.script)
        tscript.close()
        self.indentedScript = '\n'.join([' %s' % html_escape(x) for x in s])  # for restructured text in help
        self.escapedScript = '\n'.join([html_escape(x) for x in s])
        self.elog = os.path.join(self.opts.output_dir, "%s_error.log" % self.scriptname)
        if opts.output_dir:  # may not want these complexities
            self.tlog = os.path.join(self.opts.output_dir, "%s_runner.log" % self.scriptname)
            art = '%s.%s' % (self.scriptname, opts.interpreter)
            artpath = os.path.join(self.opts.output_dir, art)  # need full path
            artifact = open(artpath, 'w')  # use self.sfile as script source for Popen
            artifact.write(self.script)
            artifact.close()
        self.cl = []
        self.html = []
        self.cl.append(opts.interpreter)
        if self.treatbashSpecial and opts.interpreter in ['bash', 'sh']:
            self.cl.append(self.sfile)
        else:
            self.cl.append('-')  # stdin
        for input in opts.input_file:
            self.cl.append(input)
        if opts.output_file == 'None':  # If tool generates only HTML, set output name to toolname
            self.cl.append(str(self.scriptname) + '.out')
        self.cl.append(opts.output_file)
        for param in opts.additional_parameters:
            param, value = param.split(',')
            self.cl.append('--' + param)
            self.cl.append(value)
        self.outFormats = opts.output_format
        self.inputFormats = [formats for formats in opts.input_formats]
        self.test1Input = '%s_test1_input.xls' % self.scriptname
        self.test1Output = '%s_test1_output.xls' % self.scriptname
        self.test1HTML = '%s_test1_output.html' % self.scriptname

    def compressPDF(self, inpdf=None, thumbformat='png'):
        """need absolute path to pdf
           note that GS gets confoozled if no $TMP or $TEMP
           so we set it
        """
        assert os.path.isfile(inpdf), "## Input %s supplied to %s compressPDF not found" % (inpdf, self.myName)
        hlog = os.path.join(self.opts.output_dir, "compress_%s.txt" % os.path.basename(inpdf))
        sto = open(hlog, 'a')
        our_env = os.environ.copy()
        our_tmp = our_env.get('TMP', None)
        if not our_tmp:
            our_tmp = our_env.get('TEMP', None)
        if not (our_tmp and os.path.exists(our_tmp)):
            newtmp = os.path.join(self.opts.output_dir, 'tmp')
            try:
                os.mkdir(newtmp)
            except Exception:
                sto.write('## WARNING - cannot make %s - it may exist or permissions need fixing\n' % newtmp)
            our_env['TEMP'] = newtmp
            if not self.temp_warned:
                sto.write('## WARNING - no $TMP or $TEMP!!! Please fix - using %s temporarily\n' % newtmp)
                self.temp_warned = True
        outpdf = '%s_compressed' % inpdf
        cl = ["gs", "-sDEVICE=pdfwrite", "-dNOPAUSE", "-dUseCIEColor", "-dBATCH", "-dPDFSETTINGS=/printer", "-sOutputFile=%s" % outpdf, inpdf]
        x = subprocess.Popen(cl, stdout=sto, stderr=sto, cwd=self.opts.output_dir, env=our_env)
        retval1 = x.wait()
        sto.close()
        if retval1 == 0:
            os.unlink(inpdf)
            shutil.move(outpdf, inpdf)
            os.unlink(hlog)
        hlog = os.path.join(self.opts.output_dir, "thumbnail_%s.txt" % os.path.basename(inpdf))
        sto = open(hlog, 'w')
        outpng = '%s.%s' % (os.path.splitext(inpdf)[0], thumbformat)
        cl2 = ['convert', inpdf, outpng]
        x = subprocess.Popen(cl2, stdout=sto, stderr=sto, cwd=self.opts.output_dir, env=our_env)
        retval2 = x.wait()
        sto.close()
        if retval2 == 0:
            os.unlink(hlog)
        retval = retval1 or retval2
        return retval

    def getfSize(self, fpath, outpath):
        """
        format a nice file size string
        """
        size = ''
        fp = os.path.join(outpath, fpath)
        if os.path.isfile(fp):
            size = '0 B'
            n = float(os.path.getsize(fp))
            if n > 2**20:
                size = '%1.1f MB' % (n / 2**20)
            elif n > 2**10:
                size = '%1.1f KB' % (n / 2**10)
            elif n > 0:
                size = '%d B' % (int(n))
        return size

    def makeHtml(self):
        """ Create an HTML file content to list all the artifacts found in the output_dir
        """

        galhtmlprefix = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
        <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
        <head> <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        <meta name="generator" content="Galaxy %s tool output - see http://g2.trac.bx.psu.edu/" />
        <title></title>
        <link rel="stylesheet" href="/static/style/base.css" type="text/css" />
        </head>
        <body>
        <div class="toolFormBody">
        """
        galhtmlpostfix = """</div></body></html>\n"""

        flist = os.listdir(self.opts.output_dir)
        flist = [x for x in flist if x != 'Rplots.pdf']
        flist.sort()
        html = []
        html.append(galhtmlprefix % progname)
        html.append('<div class="infomessage">Galaxy Tool "%s" run at %s</div><br/>' % (self.scriptname, timenow()))
        fhtml = []
        if len(flist) > 0:
            logfiles = [x for x in flist if x.lower().endswith('.log')]  # log file names determine sections
            logfiles.sort()
            logfiles = [x for x in logfiles if abspath(x) != abspath(self.tlog)]
            logfiles.append(abspath(self.tlog))  # make it the last one
            pdflist = []
            npdf = len([x for x in flist if os.path.splitext(x)[-1].lower() == '.pdf'])
            for rownum, fname in enumerate(flist):
                dname, e = os.path.splitext(fname)
                sfsize = self.getfSize(fname, self.opts.output_dir)
                if e.lower() == '.pdf':  # compress and make a thumbnail
                    thumb = '%s.%s' % (dname, self.thumbformat)
                    pdff = os.path.join(self.opts.output_dir, fname)
                    retval = self.compressPDF(inpdf=pdff, thumbformat=self.thumbformat)
                    if retval == 0:
                        pdflist.append((fname, thumb))
                    else:
                        pdflist.append((fname, fname))
                if (rownum + 1) % 2 == 0:
                    fhtml.append('<tr class="odd_row"><td><a href="%s">%s</a></td><td>%s</td></tr>' % (fname, fname, sfsize))
                else:
                    fhtml.append('<tr><td><a href="%s">%s</a></td><td>%s</td></tr>' % (fname, fname, sfsize))
            for logfname in logfiles:  # expect at least tlog - if more
                if abspath(logfname) == abspath(self.tlog):  # handled later
                    sectionname = 'All tool run'
                    if (len(logfiles) > 1):
                        sectionname = 'Other'
                    ourpdfs = pdflist
                else:
                    realname = os.path.basename(logfname)
                    sectionname = os.path.splitext(realname)[0].split('_')[0]  # break in case _ added to log
                    ourpdfs = [x for x in pdflist if os.path.basename(x[0]).split('_')[0] == sectionname]
                    pdflist = [x for x in pdflist if os.path.basename(x[0]).split('_')[0] != sectionname]  # remove
                nacross = 1
                npdf = len(ourpdfs)

                if npdf > 0:
                    nacross = math.sqrt(npdf)
                    if int(nacross)**2 != npdf:
                        nacross += 1
                    nacross = int(nacross)
                    width = min(400, int(1200 / nacross))
                    html.append('<div class="toolFormTitle">%s images and outputs</div>' % sectionname)
                    html.append('(Click on a thumbnail image to download the corresponding original PDF image)<br/>')
                    ntogo = nacross  # counter for table row padding with empty cells
                    html.append('<div><table class="simple" cellpadding="2" cellspacing="2">\n<tr>')
                    for i, paths in enumerate(ourpdfs):
                        fname, thumb = paths
                        s = """<td><a href="%s"><img src="%s" title="Click to download a PDF of %s" hspace="5" width="%d"
                           alt="Image called %s"/></a></td>\n""" % (fname, thumb, fname, width, fname)
                        if ((i + 1) % nacross == 0):
                            s += '</tr>\n'
                            ntogo = 0
                            if i < (npdf - 1):  # more to come
                                s += '<tr>'
                                ntogo = nacross
                        else:
                            ntogo -= 1
                        html.append(s)
                    if html[-1].strip().endswith('</tr>'):
                        html.append('</table></div>\n')
                    else:
                        if ntogo > 0:  # pad
                            html.append('<td>&nbsp;</td>' * ntogo)
                        html.append('</tr></table></div>\n')
                logt = open(logfname, 'r').readlines()
                logtext = [x for x in logt if x.strip() > '']
                html.append('<div class="toolFormTitle">%s log output</div>' % sectionname)
                if len(logtext) > 1:
                    html.append('\n<pre>\n')
                    html += logtext
                    html.append('\n</pre>\n')
                else:
                    html.append('%s is empty<br/>' % logfname)
        if len(fhtml) > 0:
            fhtml.insert(0, '<div><table class="colored" cellpadding="3" cellspacing="3"><tr><th>Output File Name (click to view)</th><th>Size</th></tr>\n')
            fhtml.append('</table></div><br/>')
            html.append('<div class="toolFormTitle">All output files available for downloading</div>\n')
            html += fhtml  # add all non-pdf files to the end of the display
        else:
            html.append('<div class="warningmessagelarge">### Error - %s returned no files - please confirm that parameters are sane</div>' % self.opts.interpreter)
        html.append(galhtmlpostfix)
        with open(self.opts.output_html, 'w') as htmlf:
            htmlf.write('\n'.join(html))
            htmlf.write('\n')
        self.html = html

    def run(self):
        """
        scripts must be small enough not to fill the pipe!
        """
        if self.treatbashSpecial and self.opts.interpreter in ['bash', 'sh']:
            retval = self.runBash()
        else:
            if self.opts.output_dir:
                ste = open(self.elog, 'w')
                sto = open(self.tlog, 'w')
                sto.write('## Toolfactory generated command line = %s\n' % ' '.join(self.cl))
                sto.flush()
                p = subprocess.Popen(self.cl, shell=False, stdout=sto, stderr=ste, stdin=subprocess.PIPE, cwd=self.opts.output_dir)
            else:
                p = subprocess.Popen(self.cl, shell=False, stdin=subprocess.PIPE)
            p.stdin.write(self.script)
            p.stdin.close()
            retval = p.wait()
            if self.opts.output_dir:
                sto.close()
                ste.close()
                err = open(self.elog, 'r').readlines()
                if retval != 0 and err:  # problem
                    print(err, end="", file=sys.stderr)  # same problem, need to capture docker stdin/stdout
            if self.opts.make_HTML:
                self.makeHtml()
        return retval

    def runBash(self):
        """
        cannot use - for bash so use self.sfile
        """
        if self.opts.output_dir:
            s = '## Toolfactory generated command line = %s\n' % ' '.join(self.cl)
            sto = open(self.tlog, 'w')
            sto.write(s)
            sto.flush()
            p = subprocess.Popen(self.cl, shell=False, stdout=sto, stderr=sto, cwd=self.opts.output_dir)
        else:
            p = subprocess.Popen(self.cl, shell=False)
        retval = p.wait()
        if self.opts.output_dir:
            sto.close()
        if self.opts.make_HTML:
            self.makeHtml()
        return retval


def change_user_id(new_uid, new_gid):
    """
    To avoid issues with wrong user ids, we change the user id of the 'galaxy' user in the container
    to the user id with which the script has been called initially.
    """
    cmd1 = ["/usr/sbin/usermod", "-d", "/var/home/galaxy", "galaxy"]
    cmd2 = ["/usr/sbin/usermod", "-u", new_uid, "galaxy"]
    cmd3 = ["/usr/sbin/groupmod", "-g", new_gid, "galaxy"]
    cmd4 = ["/usr/sbin/usermod", "-d", "/home/galaxy", "galaxy"]
    [subprocess.call(cmd) for cmd in [cmd1, cmd2, cmd3, cmd4]]


def main():
    op = argparse.ArgumentParser()
    a = op.add_argument
    a('--docker_image', default=None)
    a('--script_path', default=None)
    a('--tool_name', default=None)
    a('--interpreter', default=None)
    a('--output_dir', default='./')
    a('--output_html', default=None)
    a('--input_file', default='None', nargs='*')
    a('--output_file', default='None')
    a('--user_email', default='Unknown')
    a('--bad_user', default=None)
    a('--make_HTML', default=None)
    a('--new_tool', default=None)
    a('--dockerized', default=0)
    a('--group_id', default=None)
    a('--user_id', default=None)
    a('--output_format', default='tabular')
    a('--input_format', dest='input_formats', action='append', default=[])
    a('--additional_parameters', dest='additional_parameters', action='append', default=[])
    opts = op.parse_args()
    assert not opts.bad_user, 'UNAUTHORISED: %s is NOT authorized to use this tool until Galaxy admin adds %s to admin_users in universe_wsgi.ini' % (opts.bad_user, opts.bad_user)
    assert os.path.isfile(opts.script_path), '## Tool Factory wrapper expects a script path - eg --script_path=foo.R'
    if opts.output_dir:
        try:
            os.makedirs(opts.output_dir)
        except Exception:
            pass
    if opts.dockerized == 0:
        retcode = switch_to_docker(opts)
        sys.exit(retcode)
    change_user_id(opts.user_id, opts.group_id)
    os.setgid(int(opts.group_id))
    os.setuid(int(opts.user_id))
    r = ScriptRunner(opts)
    retcode = r.run()
    os.unlink(r.sfile)
    if retcode:
        sys.exit(retcode)  # indicate failure to job runner


if __name__ == "__main__":
    main()
