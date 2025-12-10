<#import "template.ftl" as layout>
<#import "buttons.ftl" as buttons>

<@layout.registrationLayout displayMessage=false; section>
<!-- template: terms.ftl -->

    <#if section = "header">
        Terms and Conditions
    <#elseif section = "form">
    <div class="${properties.kcContentWrapperClass}">
        <p>By signing in you agree to these terms. Please review before continuing:</p>
        <ul>
            <li><strong>Authorized use only:</strong> Access this system solely for approved work and follow your AIIMS&apos;s policies. Unauthorized use may make you 
                liable</li>
            <li><strong>Data handling:</strong> Account data and any submitted information may be processed to operate and secure the services.</li>
            <li><strong>Security:</strong> Keep credentials confidential, use strong passwords, and report suspected compromise immediately.</li>
            <li><strong>Acceptable use:</strong> Do not upload malicious, infringing, or unlawful content, and do not attempt to bypass security controls.</li>
            <li><strong>Monitoring:</strong> Activities are logged and monitored for security and compliance purposes.</li>
            <li><strong>Confidentiality:</strong> Loggin in through this Single Sign On system may grant you access to sensitive health care and private and confidential data.
                depending on your roles and priveliges assigned. You must keep the data secure and confidential and only use it of authorized purposes. </li>
        </ul>
        <p>If you do not agree, select Decline to exit.</p>
    </div>
    <form class="${properties.kcFormClass!}" action="${url.loginAction}" method="POST">
        <@buttons.actionGroup horizontal=true>
            <@buttons.button name="accept" id="kc-accept" label="doAccept" class=["kcButtonPrimaryClass"]/>
            <@buttons.button name="cancel" id="kc-decline" label="doDecline" class=["kcButtonSecondaryClass"]/>
        </@buttons.actionGroup>
    </form>
    <div class="clearfix"></div>
    </#if>
</@layout.registrationLayout>
